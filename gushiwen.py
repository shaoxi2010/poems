from browser import get_browser_driver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from dataclasses import dataclass
from lxml import etree
from re import search
from os import path

import json
import sys
import pandas as pd


@dataclass
class GushiwenXPATH:
    # 我的收藏
    ExitLogin = "//a[text() = '退出登录']"
    NextPage = "//a[text() = '下一页']"
    PrevPage = "//a[text() = '上一页']"
    PoemBtn = "//div[@class='searchleft']/a[text() = '诗文']"
    PoetBtn = "//div[@class='searchleft']/a[text() = '古籍']"
    AuthorBtn = "//div[@class='searchleft']/a[text() = '作者']"
    Tile = "//div[@class='sons']//div[*]/a/text()"
    Author = "//div[@class='sons']//div[*]/a/span/text()"
    Link = "//div[@class='sons']//div[*]/a/@href"
    # 诗文页面
    Expand = "//a[contains(text(), '展开阅读全文')]"


class Gushiwen:
    def __init__(self):
        self.base_url = "https://so.gushiwen.cn"
        self.login_url = "https://so.gushiwen.cn/user/login.aspx"
        self.collect_url = "https://so.gushiwen.cn/user/collect.aspx"
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
        driver.get(self.login_url)
        driver.implicitly_wait(10)
        WebDriverWait(driver, 120).until(
            # 退出登陆 xpath
            EC.presence_of_element_located((By.XPATH, GushiwenXPATH.ExitLogin))
        )
        self.cookies = driver.get_cookies()

        with open(self.cookies_file, "w") as f:
            f.write(json.dumps(self.cookies))
        driver.quit()

    def login(self):
        driver = get_browser_driver(["--headless"])

        driver.get(self.login_url)
        for cookie in self.cookies:
            driver.add_cookie(cookie)

        driver.get(self.collect_url)
        try:
            WebDriverWait(driver, 10).until(
                # 退出登陆 xpath
                EC.presence_of_element_located((By.XPATH, GushiwenXPATH.ExitLogin))
            )
        except TimeoutException:
            self.login_password()
            self.login()
        self.driver = driver

    def qeury_collect(self) -> etree._Element:
        self.driver.get(self.collect_url)
        self.driver.implicitly_wait(10)

        selector = etree.HTML(self.driver.page_source)
        return selector

    def collect_poems(self) -> pd.DataFrame:
        selector = self.qeury_collect()
        titles = selector.xpath(GushiwenXPATH.Tile)
        links = selector.xpath(GushiwenXPATH.Link)
        authors = selector.xpath(GushiwenXPATH.Author)

        def extract_id(s):
            match = search(r"/shiwenv_(.*?).aspx", s)
            if match:
                return int(match.group(1), 16)
            return None

        database = zip(
            map(extract_id, links),
            titles,
            map(lambda x: x.strip(" -"), authors),
            map(lambda x: self.base_url + x.strip(), links),
        )
        return pd.DataFrame(
            data=list(database),
            columns=["id", "title", "author", "link"],
        )

    def get_poem_content(self, id, link) -> list[str]:
        self.driver.get(link)
        self.driver.implicitly_wait(10)
        for expand in self.driver.find_elements(By.XPATH, GushiwenXPATH.Expand):
            expand.click()
        selector = etree.HTML(self.driver.page_source)
        content = selector.xpath(f"//div[@id='contson{id:012x}']/p/text()")
        if not content:
            content = selector.xpath(f"//div[@id='contson{id:012x}']/text()")
        return map(lambda x: x.strip(), content)

    def pomes_content(self, df) -> pd.DataFrame:
        ids = []
        contents = []
        for _, row in df.iterrows():
            print(row)
            id, link = row["id"], row["link"]
            content = self.get_poem_content(id, link)
            ids.append(id)
            contents.append("\n".join(content))
        return pd.DataFrame(
            data=list(zip(ids, contents)),
            columns=["id", "content"],
        )


if __name__ == "__main__":
    gushiwen = Gushiwen()
    gushiwen.login()
    base = gushiwen.collect_poems()
    print(base)
    contents = gushiwen.pomes_content(base)
    print(contents)
    new = pd.merge(base, contents, on="id")
    print(new)
    sys.stdin.read()
