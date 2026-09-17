// DELIBERATELY BAD. Audit fodder for the Framework Auditor - do not copy.
package com.shopfront.tests;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.testng.Assert;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Ignore;
import org.testng.annotations.Test;

public class CheckoutTest {

    public static WebDriver driver;

    @BeforeClass
    public void setUp() {
        driver = new ChromeDriver();
        driver.manage().timeouts().implicitlyWait(30, java.util.concurrent.TimeUnit.SECONDS);
    }

    @Test
    public void payWithSavedCard() throws InterruptedException {
        driver.get("https://shopfront.example.com/cart");
        Thread.sleep(4000);

        driver.findElement(By.xpath("/html/body/div[1]/main/section[3]/button")).click();
        Thread.sleep(4000);

        driver.findElement(By.xpath("//*[@id=\"root\"]/div/div[2]/div[1]/label[1]/input")).click();
        driver.findElement(By.cssSelector("button.btn.btn--primary")).click();

        Thread.sleep(8000);

        Assert.assertTrue(driver.getPageSource().contains("Order confirmed"));
    }

    @Ignore
    @Test
    public void expiredCardIsRejected() throws InterruptedException {
        driver.get("https://shopfront.example.com/checkout");
        Thread.sleep(4000);
        driver.findElement(By.cssSelector("button.btn.btn--primary")).click();
        Thread.sleep(3000);
        Assert.assertEquals(
            driver.findElement(By.cssSelector("div.checkout__error")).getText(),
            "Card expired. Use a different card.");
    }

    @Test(enabled = false)
    public void promotionCodeApplies() throws InterruptedException {
        driver.get("https://shopfront.example.com/checkout");
        Thread.sleep(4000);
        driver.findElement(By.id("promo")).sendKeys("APRON10");
        driver.findElement(By.cssSelector("button.btn.btn--ghost")).click();
        Thread.sleep(2000);
        Assert.assertEquals(driver.findElement(By.cssSelector("dd.total")).getText(), "£21.60");
    }

    // public void deliveryAddressRequired() {
    //     driver.get("https://shopfront.example.com/checkout");
    //     Thread.sleep(4000);
    //     Assert.assertFalse(driver.findElement(By.id("pay")).isEnabled());
    // }
}
