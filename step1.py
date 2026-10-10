import requests
from bs4 import BeautifulSoup


BASE_URL = "http://hw1.alexbers.com"
BASE_HOST = "hw1.alexbers.com"
USER_TOKEN = "3f4103af406975c2abf866dc16003b94"
TIMEOUT = 30


def get_text(html):
    soup = BeautifulSoup(html, "html.parser")

    for table in soup.find_all("table"):
        table.decompose()

    return soup.get_text(" ", strip=True)


def safe_url(path):
    if path.startswith(BASE_URL + "/"):
        return path

    if path.startswith("/") and not path.startswith("//"):
        return BASE_URL + path

    raise ValueError(f"Неожиданный адрес: {path}")


def parse_table_by_keyword(html, keyword):
    if keyword not in html:
        return {}
    idx = html.find(keyword)
    doc = BeautifulSoup(html[idx:], "html.parser")
    table = doc.find("table")
    if not table:
        return {}

    result = {}
    for row in table.find_all("tr"):
        codes = row.find_all("code")
        if len(codes) == 2:
            key = codes[0].get_text(strip=True)
            val = codes[1].get_text(strip=True)
            result[key] = val
    return result


def parse_task(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    lower_text = text.lower()

    task = {
        "method": None,
        "url": None,
        "cookies": {},
        "headers": {},
        "params": {},
        "data": {},
        "files": {},
    }

    if "загрузите файлы по адресу" in lower_text:
        task["method"] = "POST"
        idx = html.find("Загрузите файлы по адресу")
        code_tag = BeautifulSoup(html[idx:], "html.parser").find("code")
        task["url"] = code_tag.get_text(strip=True) if code_tag else ""
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                codes = row.find_all("code")
                if len(codes) >= 2:
                    task["files"][codes[0].get_text(strip=True)] = codes[1].get_text(
                        strip=True
                    )

    elif "отправьте get-запрос" in lower_text:
        task["method"] = "GET"
        idx = html.find("Отправьте GET-запрос")
        code_tag = BeautifulSoup(html[idx:], "html.parser").find("code")
        task["url"] = code_tag.get_text(strip=True) if code_tag else ""

    elif "отправьте post-запрос" in lower_text:
        task["method"] = "POST"
        idx = html.find("Отправьте POST-запрос")
        code_tag = BeautifulSoup(html[idx:], "html.parser").find("code")
        task["url"] = code_tag.get_text(strip=True) if code_tag else ""

    elif "перейдите по" in lower_text:
        task["method"] = "GET"
        idx = html.find("Перейдите по")
        anchor_tag = BeautifulSoup(html[idx:], "html.parser").find("a")
        task["url"] = anchor_tag.get("href", "") if anchor_tag else ""

    else:
        return None

    task["url"] = safe_url(task["url"])

    task["params"] = parse_table_by_keyword(
        html, "При переходе выставьте следующие параметры запроса"
    )
    task["headers"] = parse_table_by_keyword(
        html, "Запрос должен иметь следующие заголовки"
    )
    task["data"] = parse_table_by_keyword(
        html, "Запрос должен иметь следующие данные формы"
    )

    cookie_dict = parse_table_by_keyword(
        html, "В запросе должны быть выставлены cookie"
    )
    if cookie_dict:
        task["cookies"].update(cookie_dict)

    return task


def execute_task(session, task):
    files = []
    for filename, content in task["files"].items():
        files.append(
            (
                "file",
                (
                    filename,
                    content.encode("utf-8"),
                ),
            )
        )

    return session.request(
        method=task["method"],
        url=task["url"],
        cookies=task["cookies"] or None,
        headers=task["headers"] or None,
        params=task["params"] or None,
        data=task["data"] or None,
        files=files or None,
        timeout=TIMEOUT,
    )


def main():
    session = requests.Session()
    session.cookies.set("user", USER_TOKEN, domain=BASE_HOST)

    try:
        response = session.get(BASE_URL + "/", timeout=TIMEOUT)
        response.raise_for_status()

        number = 1

        while True:
            task = parse_task(response.text)

            if task is None:
                print("\nОтвет сервера:")
                print(
                    BeautifulSoup(response.text, "html.parser").get_text(
                        " ", strip=True
                    )
                )
                break

            print(f"\nЗадание {number}")
            print(get_text(response.text))

            response = execute_task(session, task)
            response.raise_for_status()
            number += 1

    except (requests.RequestException, ValueError) as error:
        print("Ошибка:", error)


if __name__ == "__main__":
    main()
