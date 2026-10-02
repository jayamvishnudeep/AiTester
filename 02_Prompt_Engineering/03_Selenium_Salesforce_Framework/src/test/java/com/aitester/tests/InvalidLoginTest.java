package com.aitester.tests;

import com.aitester.pages.LoginPage;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.testng.Assert;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.Test;

public class InvalidLoginTest {

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
    public void testLoginWithInvalidPassword() {
        try {
            loginPage.doLogin("valid.user@example.com", "WrongPassword123!");
            Assert.assertTrue(loginPage.isErrorMessageDisplayed());
        } catch (Exception e) {
            Assert.fail("Failed to validate invalid password scenario", e);
        }
    }

    @Test
    public void testLoginWithUnregisteredUsername() {
        try {
            loginPage.doLogin("unregistered.user@example.com", "SomePassword123!");
            Assert.assertTrue(loginPage.isErrorMessageDisplayed());
        } catch (Exception e) {
            Assert.fail("Failed to validate unregistered username scenario", e);
        }
    }

    @Test
    public void testLoginWithMalformedUsername() {
        try {
            loginPage.doLogin("invalid-email-format", "SomePassword123!");
            Assert.assertTrue(loginPage.isErrorMessageDisplayed());
        } catch (Exception e) {
            Assert.fail("Failed to validate malformed username scenario", e);
        }
    }

    @Test
    public void testLoginWithEmptyUsername() {
        try {
            loginPage.doLogin("", "SomePassword123!");
            Assert.assertTrue(loginPage.isErrorMessageDisplayed());
        } catch (Exception e) {
            Assert.fail("Failed to validate empty username scenario", e);
        }
    }

    @Test
    public void testLoginWithEmptyPassword() {
        try {
            loginPage.doLogin("valid.user@example.com", "");
            Assert.assertTrue(loginPage.isErrorMessageDisplayed());
        } catch (Exception e) {
            Assert.fail("Failed to validate empty password scenario", e);
        }
    }

    @Test
    public void testLoginWithEmptyCredentials() {
        try {
            loginPage.doLogin("", "");
            Assert.assertTrue(loginPage.isErrorMessageDisplayed());
        } catch (Exception e) {
            Assert.fail("Failed to validate empty credentials scenario", e);
        }
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
