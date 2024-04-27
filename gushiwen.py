from browser import get_browser_driver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from dataclasses import dataclass
from lxml import etree
from re import search
from os import path, mkdir

import json
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
    poemItem = "//div[@class='sons']//div[*]/a"
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

    def quit(self):
        self.driver.quit()

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
        def extract_id(s):
            match = search(r"/shiwenv_(.*?).aspx", s)
            if match:
                return int(match.group(1), 16)
            return None

        def get_current_page():
            data = []
            items = selector.xpath(GushiwenXPATH.poemItem)
            for item in items:
                tile_author = "".join(item.itertext())
                link = item.attrib["href"]
                id = extract_id(link)
                if id:
                    tile, author = tile_author.split("-")
                    data.append(
                        (id, tile.strip(), author.strip(), self.base_url + link.strip())
                    )
                else:
                    print(f"{tile_author} 没有id!!!")
            return data

        selector = self.qeury_collect()
        database = []
        database.extend(get_current_page())

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
        contson = selector.xpath(f"//div[@id='contson{id:012x}']")
        contsontext = "\n".join(contson[0].itertext()).strip()
        return contsontext

    def pomes_content(self, df) -> pd.DataFrame:
        data = []
        for _, row in df.iterrows():
            id, link = row["id"], row["link"]
            print(f"拉取诗文: {id} {link}")
            content = self.get_poem_content(id, link)
            data.append((id, content))
        return pd.DataFrame(
            data=data,
            columns=["id", "content"],
        )

    def pandas_update_pomes(self):
        self.login()
        remote = self.collect_poems()
        if not path.exists("data"):
            mkdir("data")
        remote.to_csv("data/pomes_index.csv", index=False)
        if path.exists("data/pomes_data.csv"):
            data = pd.read_csv("data/pomes_data.csv")
            full = pd.merge(remote, data, on="id", how="left")
            # 增量拉取
            delta = full[full["content"].isnull()]
            deltadata = self.pomes_content(delta)
            data = pd.concat([data, deltadata], ignore_index=True)
        else:
            # 全局拉取
            data = self.pomes_content(remote)
        data.to_csv("data/pomes_data.csv", index=False)
        full = pd.merge(remote, data, on="id")
        self.quit()
        return full

    def pandas_pomes(self):
        if path.exists("data/pomes_index.csv") and path.exists("data/pomes_data.csv"):
            index = pd.read_csv("data/pomes_index.csv")
            data = pd.read_csv("data/pomes_data.csv")
            full = pd.merge(index, data, on="id", how="left")
            if any(full["content"].isnull()):
                return self.pandas_update_pomes()
            return full
        else:
            data = self.pandas_update_pomes()
            return data


if __name__ == "__main__":
    gushiwen = Gushiwen()
    base = gushiwen.pandas_pomes()
    print(base)
