from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver import ChromeOptions
import app


options = ChromeOptions()
options.headless = False
driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(),
                          options=options)

app.driver = driver

app.visit('https://www.duckduckgo.com/')

app.element('[name=q]')\
    .assert_text('').assert_value('')\
    .type('yashaka selene python').press_enter()

app.elements('.result__body').assert_size_greater_than(5).second\
    .assert_text('Consise').element('.result__title').click()

app.assert_text_in_title('yashaka')

app.quit()
