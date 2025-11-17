# app.py
import streamlit as st
from scraper import scrape_recipe

def main():
    st.title("Recipe Scraper")
    st.write(
        """
        1. Paste one or more recipe URLs below (one per line).  
        2. Enter your CSS selectors for the title, ingredients, instructions.  
        3. Enable "Render JavaScript" if the site is JS-heavy.  
        4. Click "Scrape Recipes" to see the results.
        """
    )

    # Multi-line input for multiple URLs
    urls_input = st.text_area(
        "Enter Recipe URLs (one per line)", 
        height=150,
        placeholder="https://example.com/recipe1\nhttps://example.com/recipe2"
    )

    # User-defined selectors
    st.subheader("CSS Selectors")
    title_selector = st.text_input("Title Selector", value="h1.recipe-title")
    ingredients_selector = st.text_input("Ingredients Selector", value="li.ingredient")
    instructions_selector = st.text_input("Instructions Selector", value=".instructions p")

    # Checkbox for rendering JavaScript
    render_js = st.checkbox("Render JavaScript?", value=False)

    # Scrape button
    if st.button("Scrape Recipes"):
        with st.spinner("Scraping in progress..."):
            # Process URLs
            urls = [url.strip() for url in urls_input.splitlines() if url.strip()]
            
            # Build the selectors dict
            selectors = {
                "title": title_selector,
                "ingredients": ingredients_selector,
                "instructions": instructions_selector
            }
            
            results = []
            for url in urls:
                recipe_data = scrape_recipe(url, selectors, render_js=render_js)
                results.append(recipe_data)

        st.success("Scraping complete!")

        # Display results
        for idx, recipe in enumerate(results, start=1):

            # Title
            st.subheader(f"**Title**: {recipe['title'] or 'N/A'}")

            st.write(f"Recipe #{idx}")
            st.write(f"**URL**: {recipe['url']}")
            
            # Ingredients
            if recipe["ingredients"]:
                st.write("**Ingredients**:")
                for ing in recipe["ingredients"]:
                    st.write(f"- {ing}")
            else:
                st.write("*No ingredients found.*")

            # Instructions
            if recipe["instructions"]:
                st.write("**Instructions**:")
                for step_idx, step in enumerate(recipe["instructions"], start=1):
                    st.write(f"{step_idx}. {step}")
            else:
                st.write("*No instructions found.*")

            st.write("---")  # Divider

if __name__ == "__main__":
    main()
