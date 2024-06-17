```
pip install cowboy
```

First create a .user file in the root directory to represent a new user. It should contain your email and OpenAI API key
```
### .user
email: helloworld@gmail.com
openai_api_key: sk-K***********************7
```

Then call
```
cowboy user init
```
to initialize your user

Next create a repo config
```
repo_name: "test_repo"
url: https://github.com/JohnPeng47/codecov-cli-neuteured.git
cov_folders: ["codecov_cli"]
interp: python # path to your Python interpreter on your local computer
```
