# Juju prometheus Blackbox exporter charm

This charm provides the [Prometheus Blackbox exporter](https://github.com/prometheus/blackbox_exporter), part of the [Prometheus](https://prometheus.io/) monitoring system

The charm should be related to the prometheus charm

## Configuration

To configure the blackbox exporter `modules` use the charm's `modules` config option.

As an example, if you store your exporter config in a local file called `modules.yaml`
you can update the charm's configuration using:

    juju config prometheus-blackbox-exporter modules=@modules.yaml

To confirm configuration was set:

    juju config prometheus-blackbox-exporter
