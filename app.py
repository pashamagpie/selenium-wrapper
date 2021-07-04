import re
from typing import Callable, List, Union

from selenium.common.exceptions import WebDriverException, \
    ElementNotInteractableException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager import driver

driver: WebDriver = ...


def visit(url):
    driver.get(url)


def wait():
    return WebDriverWait(driver, 4, poll_frequency=0.1)


def by(css_selector: str):
    return By.CSS_SELECTOR, css_selector


def wait_visible(webelement) -> WebElement:
    return wait().until(match_visibility_of_element(webelement))


def actions():
    return ActionChains(driver)


def quit():
    driver.quit()


def assert_text_in_title(value):
    wait().until(match_text_in_title(value))


class Locator(Callable[[], Union[WebElement, List[WebElement]]]):
    def __init__(self,
                 fn: Callable[[], Union[WebElement, List[WebElement]]],
                 description: str):
        self._fn = fn
        self._description = description

    def __call__(self) -> Union[WebElement, List[WebElement]]:
        return self._fn()

    def __str__(self):
        return self._description


class Element:
    def __init__(self, locator: Locator):
        self.locator = locator

    def __str__(self):
        return str(self.locator)

    def element(self, selector):
        return Element(Locator(lambda: self.locator().find_element(*by(selector)),
                               f'{self}.element({selector})'))

    def assert_text(self, value):
        wait().until(
            match_element_text(self, value),
            message=f'failed to assert "{value}" in given element')
        return self

    def assert_value(self, value):
        wait().until(match_value_of_the_element(self, value))
        return self

    def send_keys(self, keys):
        wait().until(match_passed(
            self,
            lambda its: its.send_keys(keys)
        ))
        return self

    def type(self, keys):
        wait().until(match_passed(
            self,
            lambda its: _actual_not_overlapped_element(its).send_keys(keys)
        ))
        return self

    def press_enter(self):
        self.type(Keys.ENTER)
        return self

    def click(self):
        wait().until(match_passed(self, lambda its: its.click()),
                     message='Failed to click')
        return self

    def double_click(self):
        wait().until(match_passed(
            self,
            lambda its: actions().double_click(its).perform()))
        return self

    def clear(self):
        wait().until(match_passed(
            self,
            lambda its: _actual_not_overlapped_element(its).clear()
        ))
        return self


class Elements:
    def __init__(self, locator: Locator):
        self.locator = locator

    def assert_size_greater_than(self, value):
        wait().until(match_size(self, value))
        return self

    @property
    def first(self) -> Element:
        return self[0]

    @property
    def second(self) -> Element:
        return self[1]

    def __getitem__(self, index: int):
        return Element(Locator(lambda: self.locator()[index],
                       f'{self}[{index})'))


def element(selector) -> Element:
    return Element(Locator(lambda: driver.find_element(*by(selector)),
                           f'element({selector})'))


def elements(selector) -> Elements:
    return Elements(Locator(lambda: driver.find_elements(*by(selector)),
                            f'elements({selector})'))


class match_text_in_title(object):
    def __init__(self, text):
        self.text = text

    def __call__(self, driver: WebDriver):
        actual = driver.title
        if self.text not in actual:
            raise WebDriverException(
                stacktrace=f'Expected text "{self.text}" is not present in actual page title "{actual}"'
            )
        return True


class match_visibility_of_element(object):
    def __init__(self, element: Element):
        self.element = element

    def __call__(self, driver: WebDriver):
        actual = self.element.locator().is_displayed()
        if not actual:
            raise WebDriverException(
                stacktrace=f'Actual element is hidden'
            )
        return True


class match_element_text(object):
    def __init__(self, element: Element, text):
        self.element = element
        self.text = text

    def __call__(self, driver: WebDriver):
        actual = self.element.locator().text
        if self.text not in actual:
            raise WebDriverException(
                stacktrace=f'Expected text "{self.text} is not present in actual "{actual}"'
            )
        return True


class match_value_of_the_element(object):
    def __init__(self, element: Element, text):
        self.element = element
        self.text = text

    def __call__(self, driver: WebDriver):
        value = self.element.locator().get_attribute("value")
        return self.text == value


class match_passed(object):
    def __init__(self, element: Element, command: Callable[[WebElement], None]):
        self.element = element
        self.command = command

    def __call__(self, driver: WebDriver):
        self.command(self.element.locator())
        return True


class match_size(object):
    def __init__(self, elements: Elements, value):
        self.elements = elements
        self.value = value

    def __call__(self, driver: WebDriver):
        actual = len(self.elements.locator())
        return actual > self.value


def _actual_not_overlapped_element(webelement):
    maybe_cover = driver.execute_script('''
    var element = arguments[0];
    
    var isVisible = !!( 
        element.offsetWidth 
        || element.offsetHeight 
        || element.getClientRects().length 
    ) && window.getComputedStyle(element).visibility !== 'hidden'
    
    if (!isVisible) {
        throw 'element is not visible'
    }
    
    var rect = element.getBoundingClientRect();
    var x = rect.left + rect.width/2;
    var y = rect.top + rect.height/2;
     
    var elementByXnY = document.elementFromPoint(x,y);
    
    if (elementByXnY == null) {
        return null;
    }
    
    var isNotOverlapped = element.isSameNode(elementByXnY);
    
    return isNotOverlapped ? null : elementByXnY;
    ''', webelement)
    if maybe_cover is not None:
        element_html = re.sub('\\s+', ' ',
                              webelement.get_attribute('outerHTML'))
        cover_html = re.sub('\\s', ' ', maybe_cover.get_attribute('outerHTML'))
        raise ElementNotInteractableException(
            stacktrace=f'Reason: element {element_html} is overlapped by {cover_html}')
    return webelement


