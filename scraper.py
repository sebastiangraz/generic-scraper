# scraper.py
from requests_html import HTMLSession

def scrape_recipe(url, selectors, render_js=False):
    """
    Scrapes a recipe using custom CSS selectors.
    
    :param url: The URL to scrape.
    :param selectors: A dict with keys like "title", "ingredients", "instructions"
                      and corresponding CSS selector strings.
    :param render_js: Whether to render the page with JavaScript (Pyppeteer).
    :return: A dict with the scraped data:
             {
                "url": ...,
                "title": ...,
                "ingredients": [...],
                "instructions": [...]
             }
    """
    session = HTMLSession()
    data = {
        "url": url,
        "title": None,
        "ingredients": [],
        "instructions": []
    }

    try:
        response = session.get(url)

        if render_js:
            # Render JS if needed (this can be slow)
            response.html.render(sleep=1, timeout=20)
        
        # 1) Title
        title_selector = selectors.get("title", None)
        if title_selector:
            title_elem = response.html.find(title_selector, first=True)
            if title_elem:
                data["title"] = title_elem.text.strip()

        # 2) Ingredients
        ingredients_selector = selectors.get("ingredients", None)
        if ingredients_selector:
            ingredient_elems = response.html.find(ingredients_selector)
            for elem in ingredient_elems:
                data["ingredients"].append(elem.text.strip())

        # 3) Instructions
        instructions_selector = selectors.get("instructions", None)
        if instructions_selector:
            instruction_elems = response.html.find(instructions_selector)
            for elem in instruction_elems:
                data["instructions"].append(elem.text.strip())

    except Exception as e:
        print(f"Error scraping {url} - {e}")

    return data
