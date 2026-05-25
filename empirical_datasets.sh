pip install gdown
cd ..
gdown "https://drive.google.com/file/d/1cqvyzvNBEiwnpjdsL99e1V8Re301Io9_/view?usp=sharing" -O empirical.zip
unzip empirical.zip -d empirical
mv empirical NeuralNJ/
gdown "https://drive.google.com/file/d/13C_TiRBcb8yPEhCGIDNHUq4-uYWH7iov/view?usp=sharing" -O concatenation_species_trees.zip
unzip concatenation_species_trees.zip -d concatenation_species_trees