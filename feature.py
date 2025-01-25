from playwright.sync_api import sync_playwright, TimeoutError

def extract_artist_image():
    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=True)  # Run headless to operate in the background
            context = browser.new_context()
            page = context.new_page()

            try:
                # Navigate to the AllMusic homepage
                page.goto("https://www.allmusic.com/")
                
                # Fill the search field and perform the search
                search_input_selector = 'input[name="term"]'
                page.fill(search_input_selector, "Davido")
                page.press(search_input_selector, "Enter")
                
                page.wait_for_selector("#scrollGridContainer") 
              
                image_selector = "#scrollGridContainer .artist .photo img"
                artist_image_url = page.get_attribute(image_selector, "src")
                
                if artist_image_url:
                    print("Artist Image URL:", artist_image_url)
                else:
                    print("Image not found.")
            except TimeoutError:
                print("Error: Timed out waiting for elements to load.")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

            # Close the browser
            browser.close()

    except Exception as e:
        print(f"Critical error while running Playwright: {e}")

# Run the function
extract_artist_image()

