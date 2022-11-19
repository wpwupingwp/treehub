# init
#pybabel extract -F babel.cfg -o messages.pot .
#pybabel init -i messages.pot -d translations -l zh_CN
# after translate
#pybabel compile -d translations
# update
pybabel extract -F babel.cfg -o messages.pot .
pybabel update -i messages.pot -d translations
pybabel compile -d translations
