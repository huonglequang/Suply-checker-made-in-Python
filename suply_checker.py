import sys
import sqlite3
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QListWidget, QLabel, QMenuBar, QAction, QStackedWidget,
    QPushButton, QListWidgetItem
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

class DuckDuckGoImageScraper(QThread):
    result_ready = pyqtSignal(list)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        options = Options()
        options.add_argument("--disable-gpu") #vypni GPU akceleraci
        options.add_argument("--no-sandbox") #vypni security opatření sandbox

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(f"https://duckduckgo.com/?q={self.query}&t=h_&iar=images&iax=images&ia=images")

        time.sleep(5)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        thumbs = driver.find_elements(By.TAG_NAME, "img")
        urls = []
        for img in thumbs:
            src = img.get_attribute("data-src") or img.get_attribute("src") #vem source obrázku
            if src and src.startswith("http"):
                urls.append(src)
            if len(urls) >= 10:
                break

        #kontrol jestli našel nějaký obrázky
        print("Načtené obrázky:")
        for u in urls:
            print(u)

        driver.quit()
        self.result_ready.emit(urls) #pošle seznam obrázků zpět do GUI


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(600, 300, 700, 600)
        self.setWindowTitle("Managment zboží")
        self.conn = sqlite3.connect("products.db")
        self.create_table()
        self.initUI()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            image_url TEXT
        )""")
        self.conn.commit()

    def initUI(self):
        menu = QMenuBar(self)
        self.setMenuBar(menu)

        menu_manage = QAction("Správa produktů", self)
        menu_search = QAction("Vyhledávání", self)
        menu.addAction(menu_manage)
        menu.addAction(menu_search)
        menu_manage.triggered.connect(self.show_manage_view)
        menu_search.triggered.connect(self.show_search_view)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.manage_view = QWidget()
        self.init_manage_view()
        self.stacked_widget.addWidget(self.manage_view)

        self.search_view = QWidget()
        self.init_search_view()
        self.stacked_widget.addWidget(self.search_view)

    def show_manage_view(self):
        self.stacked_widget.setCurrentWidget(self.manage_view)

    def show_search_view(self):
        self.stacked_widget.setCurrentWidget(self.search_view)

    def init_search_view(self):
        layout = QVBoxLayout(self.search_view)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Zadejte produkt a stiskněte ENTER")
        self.search_bar.returnPressed.connect(self.start_scraping)

        self.results = QListWidget()
        self.back_button = QPushButton("Zpět")
        self.back_button.clicked.connect(self.show_manage_view)

        layout.addWidget(self.search_bar)
        layout.addWidget(self.results)
        layout.addWidget(self.back_button)

    def start_scraping(self):
        query = self.search_bar.text()
        self.results.clear()
        self.results.addItem("Hledám obrázky...")
        self.scraper_thread = DuckDuckGoImageScraper(query)
        self.scraper_thread.result_ready.connect(self.display_results)
        self.scraper_thread.start()

    def display_results(self, urls):
        self.results.clear()
        if not urls:
            self.results.addItem("Nenalezeny žádné obrázky.")
            return

        for url in urls:
            widget = QWidget()
            layout = QHBoxLayout(widget)
            image_label = QLabel("Načítám...")
            image_label.setFixedSize(150, 150)
            layout.addWidget(image_label)

            try:
                img_data = requests.get(url, timeout=10).content
                pixmap = QPixmap()
                if pixmap.loadFromData(img_data):
                    image_label.setPixmap(pixmap.scaled(150, 150, Qt.KeepAspectRatio))
                else:
                    image_label.setText("Chyba načítání")
            except:
                image_label.setText("Chyba načítání")

            right = QWidget()
            right_layout = QVBoxLayout(right)
            name = self.search_bar.text()
            info = QLabel(f"Název: {name}")
            right_layout.addWidget(info)
            btn = QPushButton("Přidat produkt")
            btn.clicked.connect(lambda _, n=name, u=url: self.store_product(n, u))
            right_layout.addWidget(btn)

            layout.addWidget(right)

            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.results.addItem(item)
            self.results.setItemWidget(item, widget)

    def init_manage_view(self):
        layout = QVBoxLayout(self.manage_view)
        self.product_list = QListWidget()
        self.load_products()

        self.add_button = QPushButton("Přidat další")
        self.add_button.clicked.connect(self.show_search_view)
        self.delete_button = QPushButton("Smazat vybrané")
        self.delete_button.clicked.connect(self.delete_product)

        layout.addWidget(self.product_list)
        layout.addWidget(self.add_button)
        layout.addWidget(self.delete_button)

    def store_product(self, name, url):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO products (name, image_url) VALUES (?, ?)", (name, url))
        self.conn.commit()
        self.load_products()

    def load_products(self):
        self.product_list.clear()
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, image_url FROM products")
        for product_id, name, url in cursor.fetchall():
            widget = QWidget()
            layout = QHBoxLayout(widget)

            image_label = QLabel()
            image_label.setFixedSize(100, 100)
            try:
                img_data = requests.get(url, timeout=10).content
                pixmap = QPixmap()
                if pixmap.loadFromData(img_data):
                    image_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio))
                else:
                    image_label.setText("Chyba")
            except:
                image_label.setText("Chyba")

            info = QLabel(f"Název: {name}")
            layout.addWidget(image_label)
            layout.addWidget(info)

            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, product_id)  # <-- uloží ID produktu
            self.product_list.addItem(item) 
            self.product_list.setItemWidget(item, widget)

    def delete_product(self):
        selected = self.product_list.selectedItems()
        if not selected:
            return

        for item in selected:
            product_id = item.data(Qt.UserRole) # získá ID produktu z dat
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM products WHERE id=?", (product_id,)) # smaže produkt z databáze pomocí ID
            self.conn.commit()
            self.product_list.takeItem(self.product_list.row(item))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
