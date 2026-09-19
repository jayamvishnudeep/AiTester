package com.shopfront.tests;

import com.shopfront.pages.LoginPage;
import com.shopfront.utils.DriverFactory;
import org.openqa.selenium.WebDriver;
import org.testng.annotations.Test;

public class LoginTest {
    @Test
    public void signsInWithValidCredentials() {
        WebDriver driver = DriverFactory.create();
        new LoginPage(driver).signIn("ada@shopfront.example.com", "correct-horse");
        driver.quit();
    }
}
