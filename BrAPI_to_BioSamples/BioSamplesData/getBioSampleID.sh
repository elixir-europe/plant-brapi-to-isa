cat "$1" | curl -X POST -H "Content-Type: application/json" -d @- "http://byod.psblocal:8081/biosamples/beta/samples/"
