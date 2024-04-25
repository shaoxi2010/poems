from browser import get_browser_driver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from os import path
import json
import sys


class Gushiwen:
    def __init__(self):
        self.url = "https://so.gushiwen.cn/user/login.aspx"
        self.cookies_file = "cookies.json"
        if path.exists(self.cookies_file):
            with open(self.cookies_file, "r") as f:
                self.cookies = json.loads(f.read())
        else:
            self.login_password()

    def login_password(self):
        driver = get_browser_driver()
        driver.delete_all_cookies()
        # 等待登陆
        driver.get(self.url)
        driver.implicitly_wait(10)
        WebDriverWait(driver, 120).until(
            # 退出登陆 xpath
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="mainSearch"]/div[3]/div[1]/div[7]/a')
            )
        )
        self.cookies = driver.get_cookies()

        with open(self.cookies_file, "w") as f:
            f.write(json.dumps(self.cookies))
        driver.quit()

    def login(self):
        driver = get_browser_driver()

        driver.get(self.url)
        for cookie in self.cookies:
            driver.add_cookie(cookie)

        driver.get("https://so.gushiwen.cn/user/collect.aspx")
        try:
            WebDriverWait(driver, 10).until(
                # 退出登陆 xpath
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="mainSearch"]/div[3]/div[1]/div[7]/a')
                )
            )
        except TimeoutException:
            self.login_password()
            self.login()
        self.driver = driver


if __name__ == "__main__":
    gushiwen = Gushiwen()
    gushiwen.login()
    sys.stdin.read()
