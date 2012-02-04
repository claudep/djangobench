DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'USER'  : 'root',
        'NAME': 'django1',
        'OPTIONS': {
            'init_command': 'SET storage_engine=INNODB',
        },
        'TEST_CHARSET': 'utf8',
        'TEST_COLLATION': 'utf8_general_ci',
    },
    'other': {
        'ENGINE': 'django.db.backends.mysql',
        'USER'  : 'root',
        'NAME': 'django2',
        'OPTIONS': {
            'init_command': 'SET storage_engine=INNODB',
        },
        'TEST_CHARSET': 'utf8',
        'TEST_COLLATION': 'utf8_general_ci',
    }
}
