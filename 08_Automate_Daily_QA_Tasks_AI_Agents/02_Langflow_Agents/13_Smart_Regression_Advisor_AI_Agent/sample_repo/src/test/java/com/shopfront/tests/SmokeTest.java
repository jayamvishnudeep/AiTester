package com.shopfront.tests;

import com.shopfront.utils.DriverFactory;
import org.openqa.selenium.WebDriver;
import org.testng.annotations.Test;

public class SmokeTest {
    @Test
    public void homepageLoads() {
        WebDriver driver = DriverFactory.create();
        driver.get(System.getProperty("baseUrl"));
        driver.quit();
    }
}
