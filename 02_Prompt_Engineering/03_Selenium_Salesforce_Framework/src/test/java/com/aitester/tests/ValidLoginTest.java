package com.aitester.tests;

import com.aitester.pages.LoginPage;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.testng.Assert;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

public class ValidLoginTest {

    private WebDriver driver;
    private LoginPage loginPage;
    private static final String LOGIN_URL = "https://login.salesforce.com/?locale=in";

    @BeforeMethod
    public void setUp() {
        try {
            ChromeOptions options = new ChromeOptions();
            options.addArguments("--start-maximized");
            driver = new ChromeDriver(options);
            driver.get(LOGIN_URL);
            loginPage = new LoginPage(driver);
        } catch (Exception e) {
            throw new RuntimeException("Failed to initialize browser session", e);
        }
    }

    @Test
    public void testLoginPageTitleIsDisplayed() {
        try {
            Assert.assertTrue(driver.getTitle().toLowerCase().contains("salesforce"));
        } catch (Exception e) {
            Assert.fail("Failed to validate login page title", e);
        }
    }

    @Test
    public void testLoginFormElementsAreDisplayed() {
        try {
            Assert.assertTrue(loginPage.isUsernameFieldDisplayed());
            Assert.assertTrue(loginPage.isPasswordFieldDisplayed());
            Assert.assertTrue(loginPage.isRememberMeCheckboxDisplayed());
            Assert.assertTrue(loginPage.isLoginButtonDisplayed());
        } catch (Exception e) {
            Assert.fail("Failed to validate login form elements", e);
        }
    }

    @Test
    public void testRememberMeCheckboxIsToggleable() {
        try {
            loginPage.toggleRememberMe();
            Assert.assertTrue(loginPage.isRememberMeCheckboxDisplayed());
        } catch (Exception e) {
            Assert.fail("Failed to toggle remember me checkbox", e);
        }
    }

    @Test
    public void testLoginWithValidCredentials() {
        try {
            Properties properties = loadConfig();
            String username = System.getProperty("sf.username", properties.getProperty("sf.username"));
            String password = System.getProperty("sf.password", properties.getProperty("sf.password"));
            loginPage.doLogin(username, password);
            Assert.assertFalse(driver.getCurrentUrl().contains("login.salesforce.com"));
        } catch (Exception e) {
            Assert.fail("Failed to login with valid credentials", e);
        }
    }

    private Properties loadConfig() {
        Properties properties = new Properties();
        try (InputStream inputStream = getClass().getClassLoader().getResourceAsStream("config.properties")) {
            if (inputStream != null) {
                properties.load(inputStream);
            }
        } catch (IOException e) {
            throw new RuntimeException("Failed to load configuration file", e);
        }
        return properties;
    }

    @AfterMethod
    public void tearDown() {
        try {
            if (driver != null) {
                driver.quit();
            }
        } catch (Exception e) {
            throw new RuntimeException("Failed to close browser session", e);
        }
    }
}
