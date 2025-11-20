import configparser
import robin_stocks.robinhood as r

####### ROBINHOOD API IS SHIT AND IS NO LONGER WORKING

# def load_robinhood_credentials(config_file):
#     """
#     Load credentials from config.ini file
#     :param config_file:
#     :return:
#     """
#     # Load configuration file
#     config = configparser.ConfigParser()
#     config.read(config_file)
#     # Access credentials
#     username = config['robinhood_credentials']['username']
#     email = config['robinhood_credentials']['email']
#     password = config['robinhood_credentials']['password']
#     return(username, email, password)
#
# def login_to_robinhood(username, password):
#     """
#     Login to Robinhood API
#     :param email:
#     :param password:
#     :return:
#     """
#     try:
#         # Need to save the username and password in protected fileds
#         r.login(username=username, password=password, expiresIn=86400,
#                                scope='internal', by_sms=True, store_session=True)
#     except Exception as e:
#         print(f"Failed to log in: {e}")
#         raise