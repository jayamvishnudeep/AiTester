// DELIBERATELY BAD. Audit fodder for the Framework Auditor - do not copy.
package com.shopfront.pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.testng.Assert;

public class LoginPage {

    private WebDriver driver;

    public LoginPage(WebDriver driver) {
        this.driver = driver;
    }

    public void open() throws InterruptedException {
        driver.get("https://shopfront.example.com/login");
        Thread.sleep(2000);
    }

    public void enterEmail(String email) {
        driver.findElement(By.xpath("/html/body/div[1]/main/form/div[1]/input")).sendKeys(email);
    }

    public void enterPassword(String password) {
        driver.findElement(By.xpath("/html/body/div[1]/main/form/div[2]/input")).sendKeys(password);
    }

    public void submit() throws InterruptedException {
        driver.findElement(By.cssSelector("button.btn.btn--primary")).click();
        Thread.sleep(3000);
    }

    // A page object should not decide whether a test passes. This belongs in the test.
    public void verifyLoginSucceeded() {
        Assert.assertTrue(driver.getCurrentUrl().contains("dashboard"),
                "Expected to land on the dashboard");
    }

    public void verifyErrorMessage(String expected) {
        String actual = driver.findElement(By.cssSelector("div.auth__error > span.text-red-500")).getText();
        Assert.assertEquals(actual, expected);
    }
}
