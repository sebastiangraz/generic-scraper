import streamlit as st

from scraper import scrape_linkedin_profiles


def main() -> None:
    st.title("LinkedIn Profile Scraper (StaffSpy)")
    st.write(
        """
        Paste one or more LinkedIn profile URLs below (one per line).  
        This app uses **StaffSpy** under the hood to open a real browser, log in,
        and fetch rich profile data (experiences, skills, contact info, etc.).  

        - Limit yourself to ~100 profiles per session to stay within safe limits.  
        - You must comply with LinkedIn's terms of service and your local laws.  
        """
    )

    urls_input = st.text_area(
        "LinkedIn profile URLs (one per line)",
        height=200,
        placeholder="https://www.linkedin.com/in/dougmcmillon\nhttps://www.linkedin.com/in/satyanadella",
    )

    st.subheader("LinkedIn account configuration")
    session_file = st.text_input(
        "Session file path",
        value="linkedin_session.pkl",
        help="StaffSpy will store login cookies here so you only need to log in once.",
    )
    username = st.text_input(
        "LinkedIn email (optional if session_file already exists)",
        value="wejis42879@etramay.com",
    )
    password = st.text_input(
        "LinkedIn password (optional if session_file already exists)",
        type="password",
        value="ncw5pvn!hpg3ZDK3djz",
    )
    log_level = st.selectbox(
        "Log level",
        options=[0, 1, 2],
        index=1,
        help="0 = errors only, 1 = info, 2 = verbose (StaffSpy logs).",
    )

    if st.button("Scrape profiles"):
        urls = [u.strip() for u in urls_input.splitlines() if u.strip()]
        if not urls:
            st.warning("Please enter at least one LinkedIn profile URL.")
            return

        with st.spinner("Launching StaffSpy and scraping profiles..."):
            try:
                rows = scrape_linkedin_profiles(
                    urls,
                    session_file=session_file,
                    username=username or None,
                    password=password or None,
                    log_level=log_level,
                )
            except Exception as exc:  # pragma: no cover - runtime safety
                st.error("An error occurred while scraping with StaffSpy.")
                st.code(repr(exc))
                return

        if not rows:
            st.info(
                "No profiles were scraped. Check that your URLs are valid profile URLs.")
            return

        st.success(f"Scraped {len(rows)} profile(s).")

        for idx, row in enumerate(rows, start=1):
            st.subheader(f"Profile #{idx}")

            # Show some common fields if present.
            name = row.get("name") or row.get("full_name") or "N/A"
            position = row.get("position") or row.get("bio") or ""
            location = row.get("location") or ""
            profile_link = row.get("profile_link") or row.get(
                "profile_url") or ""

            st.write(f"**Name**: {name}")
            if position:
                st.write(f"**Position**: {position}")
            if location:
                st.write(f"**Location**: {location}")
            if profile_link:
                st.write(f"**Profile URL**: {profile_link}")

            potential_emails = row.get("potential_emails")
            if potential_emails:
                st.write("**Potential emails**:")
                if isinstance(potential_emails, (list, tuple)):
                    for email in potential_emails:
                        st.write(f"- {email}")
                else:
                    st.write(str(potential_emails))

            # Raw record for inspection.
            with st.expander("Raw data"):
                st.json(row)

            st.write("---")


if __name__ == "__main__":
    main()
