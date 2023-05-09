# Juju prometheus Blackbox exporter charm

This charm provides the [Prometheus Blackbox exporter](https://github.com/prometheus/blackbox_exporter), part of the [Prometheus](https://prometheus.io/) monitoring system

This charm is a subordinate option of the https://github.com/dparv/charm-prometheus-blackbox-peer-exporter and creates peer relation data between units related to.

Then this data can be exported using an action and added as a scrape-jobs option to a prometheus instance to provide monitoring mesh capabilities.

# Optionally AZ tagging

```
juju machines | grep -v "lxd\|Message" | awk '{print $1,$6}' | while read line; do # or any other filter that you might want
    machine=$(echo $line | awk '{print $1}'); 
    az=$(echo $line | awk '{print $2}'); 
    echo "Adding $az to machine $machine"
    juju run --machine $machine "sudo bash -c 'echo $az > /var/lib/juju/az'";
done
```

# How-to

juju deploy prometheus-blackbox-peer-exporter.charm

Wait until charm settles, all relation data to be populated, it takes some time.

juju run-action --wait prometheus-blackbox-peer-exporter/leader dump-prometheus-jobs > scrape-jobs.yaml

Edit the scrape-jobs to cleanup the headers/footers and make sure to ident the
yaml starting from the first line of the file (e.g. cut first 6 columns).

```
sed -i '1,6d' scrape-jobs.yaml
sed -i -n -e :a -e '1,6!{P;N;D;};N;ba' scrape-jobs.yaml
cut -c 7- scrape-jobs.yaml > scrape-jobs.tmp && mv scrape-jobs.tmp scrape-jobs.yaml
```

juju config prometheus scrape-jobs=@scrape-jobs.yaml

You can then import the provided grafana template to visualize the monitoring mesh.
