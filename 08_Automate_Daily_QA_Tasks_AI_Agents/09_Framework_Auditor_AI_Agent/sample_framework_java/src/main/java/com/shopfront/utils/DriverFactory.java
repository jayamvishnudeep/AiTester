// DELIBERATELY BAD. Audit fodder for the Framework Auditor - do not copy.
package com.shopfront.utils;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;

public class DriverFactory {

    // Static mutable driver shared by every test class. Nothing here can run in parallel.
    public static WebDriver driver;

    public static WebDriver getDriver() {
        if (driver == null) {
            driver = new ChromeDriver();
            driver.manage().timeouts().implicitlyWait(30, java.util.concurrent.TimeUnit.SECONDS);
        }
        return driver;
    }

    public static void sleep(int millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
        }
    }
}
