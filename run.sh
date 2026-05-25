python finetune_rl_search.py --config ./config/finetune_reinforce_search_example.yaml --instance_path ./empirical/SongD1 --infer_opt Argmax
python finetune_rl_search.py --config ./config/finetune_reinforce_search_example.yaml --instance_path ./empirical/JarvD5a --infer_opt Argmax
python finetune_rl_search.py --config ./config/finetune_reinforce_search_example.yaml --instance_path ./empirical/TarvD7 --infer_opt Argmax
python finetune_rl_search.py --config ./config/finetune_reinforce_search_example.yaml --instance_path ./empirical/WickD3b --infer_opt Argmax

python finetune_rl_search.py --config ./config/finetune_reinforce_search_example.yaml --instance_path ./empirical/SongD1 --infer_opt Search
python finetune_rl_search.py --config ./config/finetune_reinforce_search_example.yaml --instance_path ./empirical/JarvD5a --infer_opt Search
python finetune_rl_search.py --config ./config/finetune_reinforce_search_example.yaml --instance_path ./empirical/TarvD7 --infer_opt Search
python finetune_rl_search.py --config ./config/finetune_reinforce_search_example.yaml --instance_path ./empirical/WickD3b --infer_opt Search

python finetune_rl_search.py --config ./config/finetune_reinforce_search_example.yaml --instance_path ./empirical/SongD1 --infer_opt Finetune
python finetune_rl_search.py --config ./config/finetune_reinforce_search_example.yaml --instance_path ./empirical/JarvD5a --infer_opt Finetune
python finetune_rl_search.py --config ./config/finetune_reinforce_search_example.yaml --instance_path ./empirical/TarvD7 --infer_opt Finetune
python finetune_rl_search.py --config ./config/finetune_reinforce_search_example.yaml --instance_path ./empirical/WickD3b --infer_opt Finetune