mkdir -p cardtext
mkdir -p cardtext-fin
curl https://ygocdb.com/api/v0/cards.zip -o cards.zip
unzip cards.zip
rm cards.zip
python proc.py
sh s3up.sh
