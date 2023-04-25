import hydra
import torch
import pandas as pd
import os
import glob

from contrastive.utils.config import process_config
from contrastive.models.contrastive_learner_visualization import ContrastiveLearner_Visualization
from contrastive.models.contrastive_learner_with_labels import ContrastiveLearner_WithLabels
from contrastive.data.datamodule import DataModule_Evaluation


def embeddings_to_pandas(embeddings, csv_path=None, verbose=False):
    # embeddings is the output of the compute_representations function
    # csv_path is the path where to save the csv. Set to None if you want to return the df
    columns_names = ['dim'+str(i+1) for i in range(embeddings[0].shape[1])]
    values = pd.DataFrame(embeddings[0].numpy(), columns=columns_names)
    labels = embeddings[1]
    labels = pd.DataFrame(labels, columns=['ID'])
    df_embeddings = pd.concat([labels, values], axis=1)
    df_embeddings = df_embeddings.groupby('ID').mean()  # remove one copy each ID
    if verbose:
        print("embeddings:", df_embeddings.iloc[:10,:])
        print("nb of elements:", df_embeddings.shape[0])
    if csv_path:
        df_embeddings.to_csv(csv_path)
    else:
        return df_embeddings


"""The way this function works is that it creates a SimCLR structure based on the provided config,
then loads the weights of the target model (in the config). Once this is done, generate the embeddings
of the target dataset (in the config) in inference mode.
This generation methods is highly dependent of the parameters config, so I suggest either to run it right
after the training is complete, or to use evaluation/embeddings_pipeline.py to generate the embeddings (it
handles the needed modifications in order to load the right model).
This method is also relying on the current DataModule and ContrastiveLearner implementations, which means
its retro compatibility leaves a lot to be desired. 
"""
@hydra.main(config_name='config_no_save', config_path="../configs")
def compute_embeddings(config):
    config = process_config(config)

    config.mode = 'evaluation'

    # create new models in mode visualisation
    data_module = DataModule_Evaluation(config)
    data_module.setup(stage='validate')

    """# load model
    try:
        # load a model entirely saved with torch.save
        path = glob.glob(config.model_path + r'/logs/*.pt')[0]
        model = torch.load(path)
        print("Model loaded from full model save.")
    
    except:"""
    # create a new instance of the current model version then load hydra weights.
    print("No trained_model.pt saved. Create a new instance and load weights.")

    model = ContrastiveLearner_Visualization(config, sample_data=data_module)
    # fetch and load weights
    paths = config.model_path+"/logs/*/version_0/checkpoints"+r'/*.ckpt'
    if 'use_best_model' in config.keys():
        paths = config.model_path+"/logs/best_model_weights.pt"
    files = glob.glob(paths)
    print("model_weights:", files[0])
    cpkt_path = files[0]
    checkpoint = torch.load(cpkt_path, map_location=torch.device(config.device))
    model.load_state_dict(checkpoint['state_dict'])

    model.eval()

    print(config.model)
    print(config.backbone_name)

    # create folder where to save the embeddings
    embeddings_path = config.embeddings_save_path
    if 'use_best_model' in config.keys():
        embeddings_path = config.embeddings_save_path+'_best_model'
    if not os.path.exists(embeddings_path):
        os.makedirs(embeddings_path)

    # calculate embeddings for training set and save them somewhere
    print("TRAIN SET")
    train_embeddings = model.compute_representations(data_module.train_dataloader())

    # convert the embeddings to pandas df and save them
    train_embeddings_df = embeddings_to_pandas(train_embeddings)
    train_embeddings_df.to_csv(embeddings_path+"/train_embeddings.csv")

    # same thing for validation set
    print("VAL SET")
    val_embeddings = model.compute_representations(data_module.val_dataloader())

    val_embeddings_df = embeddings_to_pandas(val_embeddings)
    val_embeddings_df.to_csv(embeddings_path+"/val_embeddings.csv")

    # same thing for test set
    print("TEST SET")
    test_embeddings = model.compute_representations(data_module.test_dataloader())

    test_embeddings_df = embeddings_to_pandas(test_embeddings)
    test_embeddings_df.to_csv(embeddings_path+"/test_embeddings.csv")

    # same thing for test_intra if it exists
    if 'test_intra_csv_file' in config.keys():
        print("TEST INTRA SET")
        test_intra_embeddings = model.compute_representations(data_module.test_intra_dataloader())

        test_intra_embeddings_df = embeddings_to_pandas(test_intra_embeddings)
        test_intra_embeddings_df.to_csv(embeddings_path+"/test_intra_embeddings.csv")

    # same thing on the train_val dataset
    print("TRAIN_VAL SET")
    train_val_df = pd.concat([train_embeddings_df, val_embeddings_df],
                         axis=0)
    train_val_df.to_csv(embeddings_path+"/train_val_embeddings.csv")

    # same thing on the entire dataset
    print("FULL SET")
    full_df = pd.concat([train_embeddings_df, val_embeddings_df, test_embeddings_df],
                         axis=0)
    full_df = full_df.sort_values(by='ID')
    full_df.to_csv(embeddings_path+"/full_embeddings.csv")

    print("ALL EMBEDDINGS GENERATED: OK")


if __name__ == "__main__":
    compute_embeddings()