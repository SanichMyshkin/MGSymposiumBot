import requests


def is_url_valid(url: str) -> bool:
    try:
        response = requests.get(url)
        # Если статус код 200 (OK), то сайт доступен
        if response.status_code == 200:
            print(f"URL {url} доступен")
            return True
        else:
            print(f"URL {url} недоступен, статус код: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        # В случае ошибки соединения или недоступности ресурса
        print(f"URL {url} недоступен. Ошибка: {e}")
        return False


print(is_url_valid("https://imgur.com/2fFMhPt"))
print(is_url_valid("https://mgsu.ru/upload/iblock/f2e/f2e0cdf18217a492153c511da63ec596.jpg"))
