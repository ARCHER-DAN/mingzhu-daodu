@echo off
set DIRNAME=%~dp0
set JAVA_HOME=C:\Program Files\Amazon Corretto\jdk17.0.19_10
"%JAVA_HOME%\bin\java.exe" -cp "%DIRNAME%\gradle\wrapper\gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain %*
