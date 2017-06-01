cat "$1/$2.json" | curl -X PUT -H "Content-Type: application/json" -d @- "http://byod.psblocal:8081/biosamples/beta/samples/$2"
