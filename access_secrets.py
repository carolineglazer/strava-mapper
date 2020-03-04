def access_secret_version(project_id, secret_id, version_id):
	"""
	Access the payload for the given secret version 
	if one exists. The version can be a version 
	number as a string (e.g. "5") or an alias (e.g. 
	"latest").
	"""
	
	#Import the Secret Manager client library
	from google.cloud import secretmanager_v1beta1 as secretmanager

	#Create the Secret Manager client.
	client = secretmanager.SecretManagerServiceClient()

	#Build the resource name of the secret version.
	name = client.secret_version_path(project_id, secret_id, version_id)

	#Access the secret version.
	response = client.access_secret_version(name)

	#Print the secret payload
	payload = response.payload.data.decode('UTF-8')
	return payload

def create_secret(project_id, secret_id):
    """
    Create a new secret with the given name. A secret is a logical wrapper
    around a collection of secret versions. Secret versions hold the actual
    secret material.
    """

    # Import the Secret Manager client library.
    from google.cloud import secretmanager_v1beta1 as secretmanager

    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the parent project.
    parent = client.project_path(project_id)

    # Create the secret.
    response = client.create_secret(parent, secret_id, {
        'replication': {
            'automatic': {},
        },
    })

    # Print the new secret name.
    print('Created secret: {}'.format(response.name))

def add_secret_version(project_id, secret_id, payload):
	"""
	Add a new secret version to the given secret with the provided payload.
	"""

	# Import the Secret Manager client library.
	from google.cloud import secretmanager_v1beta1 as secretmanager

	# Create the Secret Manager client.
	client = secretmanager.SecretManagerServiceClient()

	# Build the resource name of the parent secret.
	parent = client.secret_path(project_id, secret_id)

	# Convert the string payload into a bytes. This step can be omitted if you
	# pass in bytes instead of a str for the payload argument.
	payload = payload.encode('UTF-8')

	# Add the secret version.
	response = client.add_secret_version(parent, {'data': payload})

	# Print the new secret version name.
	print('Added secret version: {}'.format(response.name))