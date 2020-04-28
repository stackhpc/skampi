{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "dsh-lmc-prototype.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "dsh-lmc-prototype.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "dsh-lmc-prototype.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Shared environment variables between all devices */}}
{{ define "dsh-lmc-prototype.shared_environment" }}
  - name: TANGO_HOST
    value: databaseds-tango-base-{{ .Release.Name }}:10000
  - name: MYSQL_HOST
    value: tangodb-tango-base-{{ .Release.Name }}:3306
  - name: MYSQL_DATABASE
    value: "{{ .Values.dshlmc.db.db }}"
  - name: MYSQL_USER
    value: "{{ .Values.dshlmc.db.user }}"
  - name: MYSQL_PASSWORD
    value: "{{ .Values.dshlmc.db.password }}"
{{- end }}