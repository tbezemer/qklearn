def _collect_results(CONFIG):
    from numpy import sqrt
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    from glob import glob
    from os import path

    results = pd.concat([pd.read_csv(f) for f in glob(path.join(CONFIG.project_path, "fold*/ML_RESULT*.csv"))])

    results.to_csv(path.join(CONFIG.project_path, "RESULTS.csv"), index=False)

    fig = plt.figure()
    ax = fig.add_subplot(111)

    ax.boxplot([sqrt(results['oob_error']) if 'oob_error' in results.columns.values else sqrt(results['train_error']), results['validation_error']])
    plt.xticks([1,2], ['OOB' if 'oob_error' in results.columns.values else 'train', 'validation'])
    plt.xlabel("Error")
    plt.ylabel("RMSE")
    plt.title("Errors for {experiment} over all folds (k={folds})".format(experiment=CONFIG.experiment_name, folds=CONFIG.KCV))
    plt.savefig(path.join(CONFIG.project_path, "SummarizedErrorPlot_{experiment_name}.png".format(experiment_name=CONFIG.experiment_name)))

def _collect_importances(CONFIG):
    import pandas as pd
    from glob import glob
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from os import path

    def process_importance(d):
            d = pd.read_csv(d)
            d.index = d['feature']
            d = d.drop(columns="feature")
            return d.transpose()

    dfs = [process_importance(f) for f in glob(path.join(CONFIG.project_path, "fold*/feature_importances_*_fold*.csv"))]

    all_importances = pd.concat(dfs, sort=True)

    all_importances.to_csv(path.join(CONFIG.project_path, "IMPORTANCES.csv"), index=False)

    bar_data = {"feature" : [], "mean" : [], "std" : []}

    for col in all_importances.columns.values:
            bar_data['feature'].append(col)
            bar_data['mean'].append(all_importances[col].mean())
            bar_data['std'].append(all_importances[col].std())
    bar_data = pd.DataFrame.from_dict(bar_data)
    bar_data = bar_data.sort_values("mean", ascending=False)
    fig = plt.figure(figsize=(20,10))
    ax = fig.add_subplot(111)
    ax.bar(x=range(0,len(bar_data)),
            height=bar_data['mean'],
            yerr=bar_data['std']
            )
    plt.xticks(range(0,len(bar_data)), bar_data['feature'], rotation='vertical')
    plt.title("Summarized Feature Importance for {experiment} over all folds (k={folds})".format(experiment=CONFIG.experiment_name, folds=CONFIG.KCV))
    plt.tight_layout()
    plt.savefig(path.join(CONFIG.project_path, "SummarizedFeatureImportancePlot_{experiment_name}.png".format(experiment_name=CONFIG.experiment_name)))

def _initialize_experiment(CONFIG):
    from os import path, system, linesep
    from shutil import copyfile

    if not path.isdir(CONFIG.project_path): system("mkdir {project_path}".format(project_path=CONFIG.project_path));
    if not path.isdir(path.join(CONFIG.project_path, CONFIG.experiment_name)): system("mkdir {project_path}".format(project_path=path.join(CONFIG.project_path, CONFIG.experiment_name)));
    if not path.isdir(path.join(CONFIG.project_path, CONFIG.experiment_name, "errors")): system("mkdir {project_path}".format(project_path=path.join(CONFIG.project_path, CONFIG.experiment_name, "errors")));
    if not path.isdir(path.join(CONFIG.project_path, CONFIG.experiment_name, "logs")): system("mkdir {project_path}".format(project_path=path.join(CONFIG.project_path, CONFIG.experiment_name, "logs")));

    experiment_config_path = path.join(CONFIG.project_path, "CONFIG_{experiment_name}".format(experiment_name=CONFIG.experiment_name))

    with open(experiment_config_path, "w") as f:

        attr = [a for a in dir(CONFIG) if not a.startswith('__') and not callable(getattr(CONFIG,a)) and not a.startswith("_") and a != "config_path"]

        f.write(linesep.join(["{param}\t{value}".format(param=param, value=getattr(CONFIG, param)) for param in attr]))


def _do_fold(train, test, i, K, X, Y, project_path):
    
    import pandas as pd
    from os import system, path

    system("mkdir {fold_path}".format(fold_path=path.join(project_path, "fold{0}".format(i))))

    print("\t\t* fold {0}".format(i, K))

    train_input, train_output = X.iloc[train], Y.iloc[train]
    validation_input, validation_output = X.iloc[test], Y.iloc[test]

    train_input.to_pickle(path.join(project_path, "fold{0}".format(i), "TRAIN_INPUT.pkl"))
    train_output.to_pickle(path.join(project_path, "fold{0}".format(i), "TRAIN_OUTPUT.pkl"))

    validation_input.to_pickle(path.join(project_path, "fold{0}".format(i), "VALIDATION_INPUT.pkl"))
    validation_output.to_pickle(path.join(project_path, "fold{0}".format(i), "VALIDATION_OUTPUT.pkl"))

def _distribute_estimator(estimator, experiment_name, project_path, fold):
    from joblib import dump
    from os.path import join
    dump(estimator, join(project_path, fold, "ESTIMATOR_{0}.pkl".format(experiment_name)))

def _distribute_metric(metric, experiment_name, project_path, fold):
    from joblib import dump
    from os.path import join
    dump(metric, join(project_path, fold, "METRIC_{0}.pkl".format(experiment_name)))

def _extract_feature_importances(CONFIG, fold, e, colnames):
    import pandas as pd
    import numpy as np
    from os import path, sep
    import matplotlib.pyplot as plt

    importances = e.feature_importances_
    std = np.std([tree.feature_importances_ for tree in e.estimators_],
                 axis=0)
    indices = np.argsort(importances)[::-1]

    # Print the feature ranking

    feature_names = [colnames[i] for i in indices]
    
    plt.figure(figsize=(20, 10))
    plt.title("Feature importances")
    plt.bar(range(len(colnames)), importances[indices],
           color="r", yerr=std[indices], align="center")
    plt.xticks(range(len(colnames)), feature_names, rotation=45)
    plt.xlim([-1, len(colnames)])
    plt.savefig(path.join(CONFIG.project_path, fold, "feature_importance_plot_{experiment_name}_{fold}.png".format(experiment_name=CONFIG.experiment_name,fold=fold.replace(sep, ''))))

    pd.DataFrame.from_dict({"feature" : feature_names, "importance" : importances[indices]}).to_csv(path.join(CONFIG.project_path, fold, 
        "feature_importances_{experiment_name}_{fold}.csv".format(experiment_name=CONFIG.experiment_name,fold=fold.replace(sep, ''))), 
        index=False)


