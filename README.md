Cowboy is a unit test generator that is meant to augment your existing test suite with more high-quality tests that raise coverage. With a simple to use commandline API, get started right now with our in-house, AI based test-generation flow.

***Note: Currently we only support Python, but other JS/TS and Golang are on the near-term roadmap***
```
pip install cowboy
```

Create a ```.user``` file in the root directory to represent a new user. It should contain your email and OpenAI API key
```
### .user
email: helloworld@gmail.com
openai_api_key: sk-K***********************7
```

Initialize your user
```
cowboy user init
```

Next create a YAML repo config. This is used to supply config options to a client running on your host, that executes your unit test suite so Cowboy can leverage the coverage information to make a more informed decision to guide our test generation process
```
repo_name: "test_repo"
url: https://github.com/JohnPeng47/codecov-cli-neuteured.git
cov_folders: ["codecov_cli"]                                        # pycoverage cov parameter: "pytest --cov=myproj tests/"
interp: python                                                      # path to python interpreter that has all the nessescary development deps to execute your unit tests
```

Create the repo ```test_repo``` from above
```
cowboy repo create test_repo.yaml
```

Setup complete! Now we can begin generating tests. Easy way to get started is to run
```
cowboy repo augment --mode=auto test_repo
``` 
Running in ```mode=auto``` will tell Cowboy to heuristically select a set of test suites for augmentation (generating new tests). Beware that this can take awhile


Augment all test suites by passing the ```mode=all``` option
```
cowboy repo augment --mode=all test_repo
```

For more fine-grained control, you can augment a specific TestModule, Cowboy's logical grouping of unit tests (maps to either a class or test_file)
```
cowboy repo augment --tm TestWoodpecker test_repo
cowboy repo augment --tm TestWoodpecker --tm TestBitrise test_repo
```

See the list of TestModules discovered for your repo
```
cowboy repo get_tms test_repo
```
