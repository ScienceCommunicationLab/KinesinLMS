# Working Files for Modal.com

Working on a solution to deploy JupyterLab sites via Modal.com

Deploy files:

`
modal deploy make_jupyter_hub.py
`

Set S3 Secret

`
modal secret aws-s3-bucket-secrets AWS_ACCESS_KEY_ID=(something) AWS_SECRET_ACCESS_KEY=(something)
`
