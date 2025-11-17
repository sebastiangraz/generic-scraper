# app.py
import streamlit as st
from scraper import scrape_generic


def _ensure_default_field_state() -> None:
    """
    Initialise the dynamic field configuration in Streamlit session state.

    Default: one \"single item\" field and one \"multiple items\" field.
    """
    if "field_configs" not in st.session_state:
        # Default to simple but valid XPath expressions.
        st.session_state.field_configs = [
            {
                "id": 1,
                "name": "Title",
                "type": "single",
                "selector": "//h1",
            },
            {
                "id": 2,
                "name": "List items",
                "type": "multiple",
                "selector": "//ul/li",
            },
        ]

    if "next_field_id" not in st.session_state:
        st.session_state.next_field_id = 3


def main():
    st.title("Generic XPath Scraper")
    st.write(
        """
        1. Paste one or more URLs below (one per line).  
        2. Configure which fields to scrape using **XPath expressions**.  
           - You can usually right-click an element in your browser devtools and **Copy full XPath**, then paste it here.  
           - **Single item**: first matching node's text (e.g. `//h1`).  
           - **Multiple items**: list of all matching nodes' text (e.g. `//ul/li`).  
           - **Image**: first matching image-like URL (e.g. `//img[@class='hero']` or `//img/@src`).  
        3. Enable "Render JavaScript" if the site is JS-heavy.  
        4. Click "Scrape" to see the results.
        """
    )

    _ensure_default_field_state()

    # Multi-line input for multiple URLs
    urls_input = st.text_area(
        "URLs by newline",
        height=150,
        placeholder="https://example.com/page1\nhttps://example.com/page2",
    )

    # Dynamic field configuration
    st.subheader("Fields to scrape")

    updated_fields = []
    for field in st.session_state.field_configs:
        cols = st.columns([1.2, 2.0])
        with cols[0]:
            name = st.text_input(
                "Field label",
                value=field.get("name", ""),
                key=f"field_name_{field['id']}",
            )
        with cols[1]:
            selector = st.text_input(
                "XPath",
                value=field.get("selector", ""),
                key=f"field_selector_{field['id']}",
            )

        # Preserve type, but show it so the user knows what they configured.
        st.caption(f"Type: **{field.get('type', 'single')}**")

        updated_fields.append(
            {
                "id": field["id"],
                "name": name,
                "type": field.get("type", "single"),
                "selector": selector,
            }
        )

        st.markdown("---")

    # Save any edits back into session state.
    st.session_state.field_configs = updated_fields

    # Dropdown + button to add new fields of different types.
    add_type_label = st.selectbox(
        "Add new field",
        options=["Single item", "Multiple items", "Image"],
        key="new_field_type_label",
    )

    add_type_map = {
        "Single item": "single",
        "Multiple items": "multiple",
        "Image": "image",
    }
    add_type = add_type_map[add_type_label]

    if st.button("Add field"):
        new_id = st.session_state.next_field_id
        st.session_state.next_field_id += 1

        default_name = {
            "single": f"Single item {new_id}",
            "multiple": f"Multiple items {new_id}",
            "image": f"Image {new_id}",
        }[add_type]

        st.session_state.field_configs.append(
            {
                "id": new_id,
                "name": default_name,
                "type": add_type,
                "selector": "",
            }
        )

    # Checkbox for rendering JavaScript
    render_js = st.checkbox("Render JavaScript?", value=False)
    debug_enabled = st.checkbox("Show debug information", value=False)

    # Scrape button
    if st.button("Scrape"):
        with st.spinner("Scraping in progress..."):
            # Process URLs
            urls = [url.strip()
                    for url in urls_input.splitlines() if url.strip()]

            # Use only fields that have a non-empty selector.
            active_fields = [
                f
                for f in st.session_state.field_configs
                if str(f.get("selector") or "").strip()
            ]

            results = []
            for url in urls:
                page_data = scrape_generic(
                    url, active_fields, render_js=render_js, debug=debug_enabled)
                results.append(page_data)

        st.success("Scraping complete!")

        # Display results
        for idx, result in enumerate(results, start=1):
            st.subheader(f"Result #{idx}")
            st.write(f"**URL**: {result.get('url')}")

            debug_info = result.get("_debug")

            for field in active_fields:
                name = (field.get("name") or "").strip() or "field"
                field_type = field.get("type", "single")
                value = result.get(name)

                if field_type == "multiple":
                    st.write(f"**{name}**:")
                    if value:
                        for item in value:
                            st.write(f"- {item}")
                    else:
                        st.write("*No items found.*")
                elif field_type == "image":
                    st.write(f"**{name}**:")
                    if value:
                        # Try to render as an image; also show the raw URL.
                        try:
                            st.image(value, caption=name)
                        except Exception:
                            # If it fails, just fall back to plain text.
                            pass
                        st.write(f"Image URL: {value}")
                    else:
                        st.write("*No image found.*")
                else:
                    st.write(f"**{name}**: {value or 'N/A'}")

            if debug_enabled and debug_info:
                with st.expander("Debug details"):
                    st.write("**HTTP**")
                    st.write(
                        f"Status: {debug_info.get('status_code')} | OK: {debug_info.get('ok')}")
                    st.write(f"Final URL: {debug_info.get('final_url')}")

                    if "error" in debug_info:
                        st.write("**Error**")
                        st.code(str(debug_info["error"]))

                    fields_debug = debug_info.get("fields") or {}
                    if fields_debug:
                        st.write("**Fields**")
                        for fname, finfo in fields_debug.items():
                            st.write(f"- **{fname}**")
                            st.write(
                                f"  - Type: `{finfo.get('type')}`  \n"
                                f"  - XPath: `{finfo.get('xpath')}`  \n"
                                f"  - Match count: {finfo.get('match_count')}"
                            )
                            sample = finfo.get("sample")
                            if sample is not None:
                                st.write("  - Sample:")
                                st.code(str(sample)[:500])

            st.write("---")  # Divider


if __name__ == "__main__":
    main()
