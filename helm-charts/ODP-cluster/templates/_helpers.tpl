{{- define "odp.defaultCpuRequest" -}}
{{- if and .Values.resources (hasKey .Values.resources "requests") (hasKey .Values.resources.requests "cpu") -}}
{{- .Values.resources.requests.cpu -}}
{{- else -}}
{{- "4" -}}
{{- end -}}
{{- end -}}

{{- define "odp.defaultMemoryRequest" -}}
{{- if and .Values.resources (hasKey .Values.resources "requests") (hasKey .Values.resources.requests "memory") -}}
{{- .Values.resources.requests.memory -}}
{{- else -}}
{{- "32Gi" -}}
{{- end -}}
{{- end -}}

{{- define "odp.defaultEphemeralRequest" -}}
{{- if and .Values.resources (hasKey .Values.resources "requests") (hasKey .Values.resources.requests "ephemeralStorage") -}}
{{- .Values.resources.requests.ephemeralStorage -}}
{{- else -}}
{{- "100Gi" -}}
{{- end -}}
{{- end -}}

{{- define "odp.defaultCpuLimit" -}}
{{- if and .Values.resources (hasKey .Values.resources "limits") (hasKey .Values.resources.limits "cpu") -}}
{{- .Values.resources.limits.cpu -}}
{{- else -}}
{{- "4" -}}
{{- end -}}
{{- end -}}

{{- define "odp.defaultMemoryLimit" -}}
{{- if and .Values.resources (hasKey .Values.resources "limits") (hasKey .Values.resources.limits "memory") -}}
{{- .Values.resources.limits.memory -}}
{{- else -}}
{{- "32Gi" -}}
{{- end -}}
{{- end -}}

{{- define "odp.defaultEphemeralLimit" -}}
{{- if and .Values.resources (hasKey .Values.resources "limits") (hasKey .Values.resources.limits "ephemeralStorage") -}}
{{- .Values.resources.limits.ephemeralStorage -}}
{{- else -}}
{{- "100Gi" -}}
{{- end -}}
{{- end -}}

# Helper to get Python version based on ODP version
{{- /*
Usage: {{ include "odp.getPythonVersion" . }}
Logic:
- if odp version starts with 3.3 then pythonVersion 311
- else if odp version starts with 3.2 then check digit after dash: if 3 then 311, if 2 then 2
- else python2
*/ -}}
{{- define "odp.getPythonVersion" -}}
  {{- if .Values.pythonVersion -}}
    {{- .Values.pythonVersion -}}
  {{- else -}}
    {{- $OdpVersion := .Values.OdpVersion | toString -}}
    {{- if hasPrefix "3.3" $OdpVersion -}}
      {{- "311" -}}
    {{- else if hasPrefix "3.2" $OdpVersion -}}
      {{- if regexMatch "-3[0-9]*$" $OdpVersion -}}
        {{- "311" -}}
      {{- else -}}
        {{- "2" -}}
      {{- end -}}
    {{- else -}}
      {{- "2" -}}
    {{- end -}}
  {{- end -}}
{{- end -}}

# Helper to get JDK version based on ODP version
{{- /*
Usage: {{ include "odp.getJdkVersion" . }}
Logic:
- if odp version starts with 3.3 then jdk 11
- else if version after "-" first digit is 3 then jdk 8
- else jdk 8
*/ -}}
{{- define "odp.getJdkVersion" -}}
  {{- if .Values.jdkVersion -}}
    {{- .Values.jdkVersion -}}
  {{- else -}}
    {{- $OdpVersion := .Values.OdpVersion | toString -}}
    {{- if hasPrefix "3.3" $OdpVersion -}}
      {{- "11" -}}
    {{- else -}}
      {{- "8" -}}
    {{- end -}}
  {{- end -}}
{{- end -}}

# Helper to get Docker repository with default fallback
{{- /*
Usage: {{ include "odp.getDockerRepository" . }}
Priority:
1. If .Values.dockerRepository is present, use it
2. If .Values.Prebake is "Yes", use prebaked repository
3. Otherwise use default repository
*/ -}}
{{- define "odp.getDockerRepository" -}}
  {{- if .Values.dockerRepository -}}
    {{- .Values.dockerRepository -}}
  {{- else if eq .Values.Prebake "Yes" -}}
    {{- "repo1.acceldata.dev:8086/odp-images/runtime-env-prebaked" -}}
  {{- else -}}
    {{- "repo1.acceldata.dev:8086/odp-images/runtime-env-base" -}}
  {{- end -}}
{{- end -}}

# Helper to generate image name based on OS, Python and JDK versions
{{- /*
Usage: {{ include "odp.getImageName" . }}
Generates image name in format: {dockerRepository}/odp-{os}-py{pythonVersion}-jdk{jdkVersion}:{tag}
Tag logic:
- If .Values.tag is defined: use that tag
- Else if Prebake is "Yes": use ODP version as tag
- Otherwise: use "latest" as tag
Examples:
- repo1.acceldata.dev:8086/odp-images/runtime-env-base/odp-rhel8-py311-jdk11:latest
- repo1.acceldata.dev:8086/odp-images/runtime-env-base/odp-rhel8-py311-jdk11:v1.0.0 (when .Values.tag is set)
- repo1.acceldata.dev:8086/odp-images/runtime-env-prebaked/odp-rhel8-py311-jdk11:3.3.6.1-1[00x] (when Prebake is Yes)
*/ -}}
{{- define "odp.getImageName" -}}
  {{- if .Values.image -}}
    {{- .Values.image -}}
  {{- else -}}
    {{- $dockerRepo := include "odp.getDockerRepository" . -}}
    {{- $os := .Values.OperatingSystem | default "rhel8" -}}
    {{- $pythonVersion := include "odp.getPythonVersion" . -}}
    {{- $jdkVersion := include "odp.getJdkVersion" . -}}
    {{- $tag := "latest" -}}
    {{- if .Values.tag -}}
      {{- $tag = .Values.tag -}}
    {{- else if eq .Values.Prebake "Yes" -}}
      {{- $tag = .Values.OdpVersion -}}
    {{- end -}}
    {{- printf "%s/odp-%s-py%s-java%s:%s" $dockerRepo $os $pythonVersion $jdkVersion $tag -}}
  {{- end -}}
{{- end -}}


{{- /*
Usage: {{ include "odp.getDatabase" . }}
Logic:
- Returns the database value from .Values.Database if it's one of: mysql, postgres, oracle, mariadb
- Otherwise defaults to mysql
*/ -}}
{{- define "odp.getDatabase" -}}
  {{- $validDatabases := list "mysql" "postgres" "oracle" "mariadb" -}}
  {{- if and .Values.Database (has .Values.Database $validDatabases) -}}
    {{- .Values.Database -}}
  {{- else -}}
    {{- "mysql" -}}
  {{- end -}}
{{- end -}}


# Helper to get HA setting with default fallback
{{- /*
Usage: {{ include "odp.getHA" . }}
Returns HA setting from .Values.HA or defaults to "No"
*/ -}}
{{- define "odp.getHA" -}}
  {{- .Values.HA | default "No" -}}
{{- end -}}
