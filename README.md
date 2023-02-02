# Open-Optimization-Studio
Web-app built with Streamlit to harness the power of Google OR-Tools' Optimization Suite in a web-based, low code environment. 


## Local Deployment

```terminal
streamlit run Open-Optimization-Studio.py
```

## Package as a "desktop app" using nativefier

1. Install [node.js](https://nodejs.org/en/download/)
2. Open Terminal/PowerShell and run the following commands (while application is running)

```terminal
npm install -g nativefier
```

```terminal
 nativefier --name '<app-name-here>' 'http://localhost:8501/' --platform '<windows -or- mac>'
```
