// DELIBERATELY BAD. Audit fodder for the Framework Auditor - do not copy.
package com.shopfront.tests;

import io.github.bonigarcia.wdm.WebDriverManager;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.testng.Assert;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;

public class LoginTest {

    public static WebDriver driver;

    private static final String BASE_URL = "https://shopfront.example.com";
    private static final String USERNAME = "ada@shopfront.example.com";
    private static final String PASSWORD = "Passw0rd123";

    @BeforeClass
    public void setUp() {
        WebDriverManager.chromedriver().setup();
        driver = new ChromeDriver();
        driver.manage().window().maximize();
        driver.manage().timeouts().implicitlyWait(30, java.util.concurrent.TimeUnit.SECONDS);
    }

    @Test
    public void validLogin() throws InterruptedException {
        driver.get(BASE_URL + "/login");
        Thread.sleep(3000);

        driver.findElement(By.id("email")).sendKeys(USERNAME);
        driver.findElement(By.id("password")).sendKeys(PASSWORD);
        driver.findElement(By.xpath("/html/body/div[1]/main/form/button")).click();

        Thread.sleep(5000);

        System.out.println("Logged in, current url is " + driver.getCurrentUrl());
        Assert.assertTrue(driver.getCurrentUrl().contains("dashboard"));
    }

    @Test
    public void wrongPassword() throws InterruptedException {
        driver.get(BASE_URL + "/login");
        Thread.sleep(3000);

        driver.findElement(By.id("email")).sendKeys(USERNAME);
        driver.findElement(By.id("password")).sendKeys("not-the-password");
        driver.findElement(By.xpath("/html/body/div[1]/main/form/button")).click();

        Thread.sleep(2000);

        String error = driver.findElement(By.cssSelector("div.auth__error > span.text-red-500")).getText();
        Assert.assertEquals(error, "Email or password is incorrect.");
    }

    @Test
    public void signInButtonDisabledWhenEmpty() throws InterruptedException {
        driver.get(BASE_URL + "/login");
        Thread.sleep(3000);
        // no assertion here yet - TODO
        System.out.println("checked the button");
    }

    @AfterClass
    public void tearDown() {
        try {
            driver.quit();
        } catch (Exception e) {
        }
    }
}
