# Supply Checker (Product Management Tool)

A PyQt5 desktop application for managing products and retrieving images using DuckDuckGo image search and Selenium.

## Features

- Add and manage product list with images
- Fetch product images using DuckDuckGo image search
- SQLite database for storing product information
- Uses Selenium for image scraping

## How to Run

1. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Make sure you have Google Chrome installed.

3. Run the app:
   ```bash
   python suply_checker.py
   ```

## Notes

- This app uses `webdriver-manager` to automatically manage the ChromeDriver.
- Internet connection is required for image scraping.
