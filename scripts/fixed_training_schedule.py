"""Training CLI construction, independent of PyTorch/CUDA imports."""


def training_arguments(upstream,source,output,config,saves,tests):
    if not saves or not tests or any(i<=0 for i in list(saves)+list(tests)):
        raise ValueError("Checkpoint iterations must be positive")
    return [str(upstream/"train.py"),"-s",str(source),"--model_path",str(output/"model"),
        "--configs",str(config),"--expname","true-skate-fixed-pilot",
        "--save_iterations",*[str(i) for i in saves],
        "--test_iterations",*[str(i) for i in tests],"--ip","127.0.0.1","--port","6010"]
