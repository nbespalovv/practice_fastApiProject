import re
import time

from bs4 import BeautifulSoup as bs
from celery import Celery
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys


class Crawler:
    def __init__(self, url):
        self.url = url

    def get_soup(self):
        #         soup = BeautifulSoup(requests.get(self.url).text, "html.parser")
        driver = webdriver.Chrome()
        driver.get(self.url)
        source_data = driver.page_source
        soup = bs(source_data)

        return soup


class Ctrl:
    def __init__(self):
        pass

    # n - количество коленьев, которое задает пользователь
    def get_link_and_parse(self, name, n):

        # получение ссылки на актера
        url = Parser().get_link_actor(name)
        # получение ссылок на фильмы, в которых он снимался
        link_films = Parser().get_info_actor(url)
        links_emp = []

        for link in link_films:
            # получение ссылок на друзей актера
            link_employees = Parser().get_info_film(link)
            for link_emp in link_employees:
                Parser().get_info_actor(link_emp)
                links_emp.append(link_emp)
            print(links_emp)

        for _ in range(n - 1):
            links_emp = []
            for link_emp in links_emp:
                # получение ссылок на фильмы, в которых он снимался
                link_films = Parser().get_info_actor(link_emp)

                # обход этих ссылок по одной
                for link in link_films:
                    # получение ссылок на друзей актера
                    link_employees = Parser().get_info_film(link)
                    for link_emp in link_employees:
                        Parser().get_info_actor(link_emp)
                        links_emp.append(link_emp)
                    print(links_emp)


class Parser:
    def __init__(self):
        pass

    # получение ссылки для определенного актера, имя которого вводит пользователь
    def get_link_actor(self, name):

        driver = webdriver.Chrome()
        driver.get('https://ru.kinorium.com/')
        input_tab = driver.find_element(By.CLASS_NAME, 'ui-autocomplete-input')
        input_tab.send_keys(name)
        input_tab.send_keys(Keys.ENTER)
        tab_actor = driver.find_element(By.XPATH,
                                        '/html/body/div[6]/div/div[6]/div[1]/div/div/div[2]/div/div[3]/div[1]/h3/a')
        tab_actor.send_keys(Keys.ENTER)

        return driver.current_url

    # получение информации об актерах, возвращает все ссылки фильмов, в которых снимался данный актер
    def get_info_actor(self, url):

        soup = Crawler(url).get_soup()
        time.sleep(7)

        id_actor = re.findall(r'\d+', url)
        name = soup.find('div', class_='person-page__title-elements-wrap').text.replace(u'\xa0', u' ').strip()

        try:
            birthdate = soup.find('div', class_='person_info').find('meta', itemprop='birthDate').get('content')

        except Exception as E:
            birthdate = 'no birthdate'

        try:
            gender = soup.find('div', class_='person_info').find('meta', itemprop='gender').get('content')

        except Exception as E:
            gender = 'no gender'

        link_films = []
        id_films = []
        for link in soup.findAll('div', class_='item headlines_type-actor'):
            link_film = 'https://ru.kinorium.com' + link.find('a', class_='filmList__item-title').get('href')
            link_films.append(link_film)
            id_films.append(re.findall(r'\d+', link_film))

        # этот массив добавлять в таблицу actor
        info_actor = [id_actor, name, gender, birthdate, id_films]
        print(info_actor)

        return link_films

    # получение информации о фильме, возвращает ссылки на всех людей, которые учавствовали в съёмках
    def get_info_film(self, link):

        id_film = re.findall(r'\d+', link)

        soup = Crawler(link).get_soup()

        name = soup.find('h1', class_='film-page__title-text').text
        time.sleep(7)

        try:

            countries = []
            for country in soup.findAll('a', class_='film-page__country-link'):
                countries.append(country.text)

            genres = []
            for genre in soup.findAll('li', itemprop='genre'):
                genres.append(genre.text)

            warning = {}

            for par_con in soup.find('tr', class_='film-page__parentalguide-toggle-line').findAll('li'):
                parental_control_count = par_con.find('p').text
                parental_control = par_con.text
                parental_control = parental_control.replace(parental_control_count, '')

                warning[parental_control] = parental_control_count

        except Exception as E:
            warning = 'no parental control'

        # этот массив добавлять в таблицу films
        info_films = [name, link, warning, countries, genres]

        print(info_films)
        time.sleep(7)

        soup_cast = Crawler(link + 'cast').get_soup()

        employees = {}
        emp_links = []
        for t in soup_cast.findAll('div', class_='ref-list clearfix'):

            for pos in t.findAll('h1', class_='cast-page__title'):
                position = pos.text.strip()
                employees[position] = []

            for emp in t.findAll('a', class_='cast-page__link-name link-info-persona-type-persona'):
                employee = emp.get('href')
                emp_link = 'https://ru.kinorium.com/' + employee
                emp_links.append(emp_link)
                employee_id = re.findall(r'\d+', employee)
                employees[position].append(employee_id)

        return emp_links


celery = Celery('web', broker='redis://localhost:6379')


@celery.task
def parse_website(name):
    print(f"Запущен процесс на имя {name}")
    Ctrl().get_link_and_parse(name, 2)