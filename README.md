## Jacoco Live

This application is used to report the live coverage data from the Jacoco agent. Its opens a REST API and when the API is called, it records the current overall coverage, the coverage change since last time, and the newly covered lines. The output will be written into a yaml file, with records in chronological order.

### Usage
Install `yaml` and `flask` to your Python environment if not already installed:
```
pip install pyyaml
pip install flask
```

First launch the monitored application with Jacoco agent, then start this application.
```
python main.py --classfiles [path to the class files of the monitored app] --sourcefiles [path to the sources files of the monitored app] --cli [path to jacococli.jar] --address [address of the Jacoco agent (default: localhost)] --port [Jacoco agent port (default: 6300)] --output [output file (default: coverage_log.yaml)] --host [this app's host (default: 0.0.0.0)] --flask-port [this app's port (default: 5000)]
```

As long as this app is running, ask it to record the coverage:
```
curl http://localhost:5000/refresh
```

Example output as follows. It shows the overall coverage data, the increase of coverage data sicne last time, and the lines that are newly covered.
```yaml
- timestamp: '2025-04-22T18:29:27.911462'
  overall_coverage:
    INSTRUCTION:
      covered: 3499
      total: 17197
      percent: 20.346572076524975
    LINE:
      covered: 749
      total: 3580
      percent: 20.921787709497206
    BRANCH:
      covered: 165
      total: 1353
      percent: 12.195121951219512
  coverage_change:
    INSTRUCTION:
      covered: 16
      total: 17197
      percent: 0.09303948363086585
    BRANCH:
      covered: 1
      total: 1353
      percent: 0.07390983000739099
    LINE:
      covered: 4
      total: 3580
      percent: 0.11173184357541899
  newly_covered_lines:
    org/heigit/ohsome/ohsomeapi/executor/AggregateRequestExecutor.java:
    - 87
    - 88
    org/heigit/ohsome/ohsomeapi/controller/dataaggregation/elements/CountController.java:
    - 47
    - 49

```