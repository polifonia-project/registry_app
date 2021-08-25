import os , json
import requests
from github import Github, InputGitAuthor
import conf
# based on https://towardsdatascience.com/all-the-things-you-can-do-with-github-api-and-python-f01790fca131


dir_path = os.path.dirname(os.path.realpath(__file__))


def get_github_users(userlogin):
	is_valid_user = False
	if conf.token != '' and conf.owner != '' and conf.repo_name != '':
		# req = requests.get("https://api.github.com/repos/"+conf.owner+"/"+conf.repo_name+"/collaborators",
		# 					headers={"Authorization": "token "+conf.token})
		req = requests.get("https://api.github.com/repos/"+conf.owner+"/"+conf.repo_name+"/collaborators",
							headers={"Authorization": "token "+conf.token})
		if req.status_code == 200:
			print([user for user in req.json()])
			users = [user['login'] for user in req.json()]
			if userlogin in users:
				is_valid_user = True
	return is_valid_user


def push(local_file_path, branch=None):
	""" create a new file or update an existing file.
	the remote file has the same relative path of the local one"""

	token = conf.token
	owner = conf.owner
	repo_name = conf.repo_name
	g = Github(token)
	repo = g.get_repo(owner+"/"+repo_name)
	author = InputGitAuthor(conf.author,conf.author_email) # commit author
	remote_file_path ="/contents/"+local_file_path # check if the file exists in repo

	try:
		contents = repo.get_contents(local_file_path) # Retrieve the online file to get its SHA and path
		update=True
		message = "updated file "+local_file_path
	except:
		update=False
		message = "created file "+local_file_path

	with open(local_file_path) as f: # Both create/update file replace the file with the local one
		data = f.read() # could be done in a smarter way

	if update == True:  # If file already exists, update it
		repo.update_file(contents.path, message, data, contents.sha, author=author)  # Add, commit and push branch
	else:  # If file doesn't exist, create it in the same relative path of the local file
		repo.create_file(local_file_path, message, data, branch=branch, author=author)  # Add, commit and push branch
