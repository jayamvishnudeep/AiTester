package com.shopfront.utils;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;

public class DriverFactory {
    public static WebDriver create() {
        return new ChromeDriver();
    }
}
