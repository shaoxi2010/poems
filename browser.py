from selenium import webdriver
from platform import system
from subprocess import check_call
from os import path
from typing import List

def get_stealth_min_js():
    if path.exists("stealth.min.js"):
        return
    check_call(["npx", "extract-stealth-evasions"])

def get_browser_driver(args: List[str] = None):
    # safari 有个透明的窗口，所以不支持
    if system() == "Windows":
        options = webdriver.EdgeOptions()
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        if args is not None:
            for arg in args:
                options.add_argument(arg)
        options.add_argument('--disable-blink-features=AutomationControlled')
        driver = webdriver.Edge(options=options)
    else:
        options = webdriver.ChromeOptions()
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        if args is not None:
            for arg in args:
                options.add_argument(arg)
        options.add_argument('--disable-blink-features=AutomationControlled')
        driver = webdriver.Chrome(options=options)
    get_stealth_min_js()
    with open('stealth.min.js') as stealth:
        stealthjs = stealth.read()
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": stealthjs
        })
    return driver


if __name__ == "__main__":
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    driver = get_browser_driver()
    driver.delete_all_cookies()
    print(driver.get_cookies())
    driver.get("https://so.gushiwen.cn/user/login.aspx")
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 120).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="mainSearch"]/div[3]/div[1]/div[7]/a'))
    )
    print(driver.get_cookies())
    driver.add_cookie