mkdir -p cardtext-fin
for i in $(ls cardtext/) ; do
    scp -P8765 cardtext/$i root@raye:/volume/webroot/cardtext/$i && \
    mv cardtext/$i cardtext-fin/$i
done
mkdir -p ../pics/thumb
mkdir -p ../cardpic-fin
for path in ../pics/*.jpg ; do
    [ -e "$path" ] || break
    chmod 644 "$path"
    i=$(basename "$path")
    scp -P8765 "$path" root@raye:/volume/webroot/cardpic/$i && \
    mv "$path" ../cardpic-fin/$i
done
mkdir -p ../cardpic-fin/thumb
for path in ../pics/thumb/*.jpg ; do
    [ -e "$path" ] || break
    chmod 644 "$path"
    i=$(basename "$path")
    scp -P8765 "$path" root@raye:/volume/webroot/cardpic/thumb/$i && \
    mv "$path" ../cardpic-fin/thumb/$i
done
