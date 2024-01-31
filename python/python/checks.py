import pandas as pd
import numpy as np
import re
import datetime
import warnings
import inspect
import os
import lares
from datetime import datetime, timedelta

OPTS_PDN = ["positive", "negative", "default"]

HYPS_NAMES = ["thetas", "shapes", "scales", "alphas", "gammas", "penalty"]

HYPS_OTHERS = ["lambda", "train_size"]

LEGACY_PARAMS = ["cores", "iterations", "trials", "intercept_sign", "nevergrad_algo"]


def check_nas(df: pd.DataFrame):
    name = df.__repr__()
    ## Manually added df.isna().sum() instead of `np.count_nan(df)`
    if df.any().isna().sum() > 0 or df.any().isnull().sum() > 0: ## added any()
        ## naVals = lares.missingness(df) ## Lares Missingness determines the naVal Columns
        null_columns = df.columns[df.isnull().any()] ## lares.missingness(df) checks for missing values, this line checks for nulls
        na_columns = df.columns[df.isna().any()] ## lares.missingness(df) checks for missing values, this line checks for na
        cols = null_columns.append(na_columns)
        raise ValueError("Dataset {} contains missing (NA) values.".format(name) + "\nThese values must be removed or fixed "
              "for Robyn to properly work.\nMissing values: {}, ".format(', '.join([cols[i] for i in range])) ## Manually added ValueError
     )
    ## have_inf = [sum(np.isposfinite(x)) for x in df]
    ## Manually changed to, may need to change?
    inf_count = np.isinf(df.all()).values.sum()
    if inf_count: ## removed any to > 0
        col_names = df.columns.to_series()[np.isinf(df).all()]  ## manually added.
        # col_names= ','. join([ names[i] for i , _ in   enumerategenerator])
        raise ValueError("Dataset " + name + "contains Inf values".format(col_names[:-2]) + "having an infinite number of nans\nCheck:"+ ", ".join([col_names[_]] for _, val in zip(enumerate(0)))) ## Manually added ValueError


def check_novar(dt_input, InputCollect=None):
    ## Manual: lares package required?
    ## zerovar method checks for each column:
    ## novar = dt_input.apply(lambda x: x.var() == 0, axis=1)
    novar_columns = list(dt_input.loc[:,dt_input.nunique()==1].columns)
    if len(novar_columns) > 0:
        msg = f"There are {len(novar_columns)} column(s) with no-variance: {novar_columns}"
        if InputCollect is not None:
            msg += f"Please, remove the variable(s) to proceed...\n>>> Note: there's no variance on these variables because of the modeling window filter ({InputCollect['window_start']}:{InputCollect['window_end']})"
        ## Manual : No else case present in the original code.
        ## else:
        ##    msg += "Please, remove the variable(s) to proceed..."
        raise ValueError(msg)


def check_varnames(dt_input, dt_holidays, dep_var, date_var, context_vars, paid_media_spends, organic_vars):
    ## dt_input.name = 'dt_input' ## Manual: Added name
    ## dt_holidays.name = 'dt_holidays' ## Manual: Added name

    ## Manually changed to dict, to get its name correctly, name of the variable is lost after converting it to list
    dfs = {"dt_input" : dt_input, "dt_holidays" : dt_holidays}

    for table_name, table in dfs.items():
        ## table_name = key , commented out since, in R code it can read the variable name after it is converted to list

        if table_name == "dt_input":
            var_lists = [dep_var, date_var, context_vars, paid_media_spends, organic_vars, "auto"]
        ## elif table_name == "dt_holidays":, commented out since no else case defined in R code.
        if table_name == "dt_holidays":
            var_lists = ["ds", "country"]
        ## else:, commented out since no else case defined in R code.
        ##    continue

        df = dfs[table_name] ## Manually added access by key instead of index since dfs is a dict.
        ## table_var_list = [var for var in var_lists if var != "auto"], commented out since var lists is a lists of lists therefore additional column name checks can't be performed, flattened list is required.

        table_var_list = list()
        for var in var_lists:
            if isinstance(var, list):
                for v in var:
                    table_var_list.append(v)
            elif var != "auto":
                table_var_list.append(var)

        # Duplicate names
        ## unique_names = set(var_lists) ## Manual: Changed from list to set
        unique_names = [*table_var_list]
        if len(table_var_list) != len(unique_names):
            these = [var for var in table_var_list if df[var].value_counts() > 1]
            raise ValueError(f"You have duplicated variable names for {table_name} in different parameters. Check: {', '.join(these)}")

        # Names with spaces
        with_space = [var for var in table_var_list if re.search("\s+", var)]
        if any(with_space):
            raise ValueError(f"You have invalid variable names on {table_name} with spaces. Please fix columns: {', '.join(with_space)}")


def check_datevar(dt_input, date_var="auto"):
    """
    Checks if the date variable is correct and returns a dictionary with the date variable name,
    interval type, and a tibble object of the input data.
    """
    # Convert dt_input to a pandas DataFrame
    ## Manually commented out: dt_input = pd.DataFrame(dt_input)

    # Check if date_var is auto
    if date_var == "auto":
        # Find the first column that contains dates
        is_date = np.where(dt_input.apply(lambda x: isinstance(x, datetime.date)).any())[0]

        # If only one date column is found, set date_var to its name
        if len(is_date) == 1:
            date_var = dt_input.columns[is_date[0]]
            print(f"Automatically detected 'date_var': {date_var}")
        else:
            # If multiple date columns are found, raise an error
            raise ValueError("Can't automatically find a single date variable to set 'date_var'")

    # Check if date_var is valid
    ## Manually added instance and length check since string has len > 1 for "DATE", always fails
    if date_var is None or (True if isinstance(date_var, list) and len(date_var) > 1 else False) or date_var not in dt_input.columns:
        raise ValueError("You must provide only 1 correct date variable name for 'date_var'")

    # Arrange the data by the date variable
    # dt_input = dt_input.reindex(columns=[date_var])
    # print("Debug input checks 117: \n", dt_input)

    # Convert the date variable to a Date object
    # dt_input[date_var] = pd.to_datetime(dt_input[date_var], origin="1970-01-01")
    ## Manually added
    dt_input[date_var] = dt_input[date_var].apply(pd.to_datetime)

    # Check if the date variable contains duplicates or invalid dates
    date_var_dates = [dt_input[date_var].iloc[0], dt_input[date_var].iloc[1]]
    ## Added manually
    date_var_dates_set = set(date_var_dates)

    # if any(table(date_var_dates) > 1): manually commented out , need to count date_var_dates
    if len(date_var_dates) > len(date_var_dates_set): ## Added manually
        raise ValueError("Date variable shouldn't have duplicated dates (panel data)")

    if pd.isnull(np.array(date_var_dates)).any() or any(anydate == 'Inf' for anydate in date_var_dates): ## anydate_var_dates).any(): ## Manually changed to isNaN
        raise ValueError("Dates in 'date_var' must have format '2020-12-31' and can't contain NA nor Inf values")

    # Calculate the interval between the first two dates
    dayInterval = (date_var_dates[1] - date_var_dates[0]).days

    # Determine the interval type (day, week, or month)
    intervalType = None
    if dayInterval == 1:
        intervalType = "day"
    elif dayInterval == 7:
        intervalType = "week"
    elif dayInterval in range(28, 31):
        intervalType = "month"
    else:
        raise ValueError(f"{date_var} data has to be daily, weekly or monthly")

    # Return a dictionary with the results
    output = {
        "date_var": date_var,
        "dayInterval": dayInterval,
        "intervalType": intervalType,
        "dt_input": dt_input
    }

    return output


def check_depvar(dt_input, dep_var, dep_var_type):
    if dep_var is None:
        raise ValueError("Must provide a valid dependent variable name for 'dep_var'")
    if dep_var not in dt_input.columns:
        raise ValueError("Must provide a valid dependent name for 'dep_var'")
    if isinstance(dep_var, list) and len(dep_var) > 1: ## Manually changed
        raise ValueError("Must provide only 1 dependent variable name for 'dep_var'")
    ## if not (dt_input[dep_var].dtypes.isnumeric() or dt_input.iloc[:, dep_var].dtypes.isinteger()):
    ## Added manually
    if not (issubclass(dt_input[dep_var].dtypes.type, np.float64) or issubclass(dt_input[dep_var].dtypes.type, np.integer)):
        raise ValueError("'dep_var' must be a numeric or integer variable")
    if dep_var_type is None:
        raise ValueError("Must provide a dependent variable type for 'dep_var_type'")
    if dep_var_type not in ["conversion", "revenue"]:
        raise ValueError("'dep_var_type' must be 'conversion' or 'revenue'")
    ## if len(dep_var_type) != 1, R checks for length for string but no need in Python.


def check_prophet(dt_holidays, prophet_country, prophet_vars, prophet_signs, day_interval):
    # Check if prophet_vars is a valid vector
    ## Manual: Commented out this and called check_vector
    ## if not isinstance(prophet_vars, list) or not all(isinstance(x, str) for x in prophet_vars):
    ##    raise ValueError("prophet_vars must be a list of strings")

    check_vector(prophet_vars)

    if prophet_signs is not None:
        check_vector(prophet_signs)

    ## Wrong translation
    # Check if prophet_signs is a valid
    ## if not isinstance(prophet_signs, list) or not all(isinstance(x, str) for x in prophet_signs):
    ##    raise ValueError("prophet_signs must be a list of strings")
    ## Manually added
    if dt_holidays is None or prophet_vars is None:
        return None

    ## Wrong Translation
    # Check if prophet_country is a valid string
    ## if prophet_country is None or not isinstance(prophet_country, str):
        ## raise ValueError("prophet_country must be a string")

    prophet_vars = [(v.lower()) for v in prophet_vars] ## Manually added

    opts = ["trend", "season", "monthly", "weekday", "holiday"] ## Manually added

    # Check if prophet_vars contains holiday and prophet_country is not None
    if "holiday" not in prophet_vars:
        if prophet_country is not None: ## Manually added nested ifs
            ## warnings.warn("Ignoring prophet_vars = 'holiday' input given your data granularity")
            warnings.warn(f"Input 'prophet_country' is defined as {prophet_country} but 'holiday' is not setup within 'prophet_vars' parameter")
        prophet_country = None ## Manually added

    if not all(pv in opts for pv in prophet_vars): ## Manually added
        raise ValueError(f"Allowed values for `prophet_vars` are:  {opts}") ## Manually added

    # Check if prophet_vars contains weekday and day_interval > 7
    if "weekday" in prophet_vars and day_interval > 7:
        warnings.warn("Ignoring prophet_vars = 'weekday' input given your data granularity")

    # Check if prophet_country is not in dt_holidays$country
    ## Manually added: Changed a lot
    if "holiday" in prophet_vars and (prophet_country is None or prophet_country not in dt_holidays["country"].values):
        ## raise ValueError(f"prophet_country must be one of the countries in dt_holidays$country, got {prophet_country}")
        unique_countries = set(dt_holidays["country"].values)
        country_count = len(unique_countries)
        raise ValueError(f"You must provide 1 country code in 'prophet_country' input. {country_count} countries are included: {unique_countries} If your country is not available, manually include data to 'dt_holidays' or remove 'holidays' from 'prophet_vars' input.")

    ## Manually added
    if prophet_signs is None:
        prophet_signs = ["default"] * len(prophet_vars)

    # Check if prophet_signs is a valid vector of strings
    if not all(x in OPTS_PDN for x in prophet_signs):
        raise ValueError(f"Allowed values for 'prophet_signs' are: {', '.join(OPTS_PDN)}")

    # Check if prophet_signs has the same length as prophet_vars
    if len(prophet_signs) != len(prophet_vars):
        raise ValueError("'prophet_signs' must have the same length as 'prophet_vars'")

    return prophet_signs

## Converted using Code Lama 34B
def check_context(dt_input, context_vars, context_signs):
    if context_vars is not None:
        if context_signs is None:
            context_signs = ["default"] * len(context_vars) ## Manually corrected
        if not all(sign in OPTS_PDN for sign in context_signs): ## Manually corrected
            raise ValueError("Allowed values for 'context_signs' are: " + ", ".join(OPTS_PDN))
        if len(context_signs) != len(context_vars):
            raise ValueError("Input 'context_signs' must have same length as 'context_vars'")
        temp = [var in dt_input.columns for var in context_vars]
        if not all(temp):
            raise ValueError("Input 'context_vars' not included in data. Check: " + str(context_vars[~temp]))
        return context_signs


def check_vector(x):
    ## In R, lists could be like dicts, therefore in this one it checks if it is an array without names (keys)
    ## if isinstance(x, pd.DataFrame) or isinstance(x, list):, manually changed to below
    if not isinstance(x, list): ##  or not isinstance(type(x, np.array.):
        raise ValueError(f"Input '{x}' must be a valid vector")


def check_paidmedia(dt_input, paid_media_vars, paid_media_signs, paid_media_spends):
    # Check if paid_media_spends is provided
    if paid_media_spends is None:
        raise ValueError("Must provide 'paid_media_spends'")

    # Check if paid_media_vars is a vector,
    ## Manually added, check_vector, commented out the check
    ## if not isinstance(paid_media_vars, list):
    ##    raise ValueError("'paid_media_vars' must be a vector")
    check_vector(paid_media_vars)

    # Check if paid_media_signs is a vector
    paid_media_signs = list() ## Manually added, check_vector, commented out the check, check_vector in R also checks if empty
    check_vector(paid_media_signs)
    ## if not isinstance(paid_media_signs, list):
    ##     raise ValueError("'paid_media_signs' must be a vector")

    # Check if paid_media_spends is a vector
    ## Manually added, check_vector, commented out the check
    ## if not isinstance(paid_media_spends, list):
    ##    raise ValueError("'paid_media_spends' must be a vector")
    ## Manully commented out check_adstock(paid_media_spends)
    check_vector(paid_media_spends)

    # Check length of paid_media_vars, paid_media_signs, and paid_media_spends
    media_var_count = len(paid_media_vars)
    spend_var_count = len(paid_media_spends)

    ## Manual, wrong interpretation
    # Check if paid_media_signs is a scalar or a vector of the same length as paid_media_vars
    ## if not (isinstance(paid_media_signs, int) or (isinstance(paid_media_signs, list) and len(paid_media_signs) == media_var_count)):
    ##    raise ValueError("'paid_media_signs' must be a scalar or a vector of the same length as 'paid_media_vars'")

    # Check if paid_media_vars are in dt_input
    temp = [var in dt_input.columns for var in paid_media_vars]
    if not all(temp): ## Manually corrected
        raise ValueError("Input 'paid_media_vars' not included in data. Check: " + str(paid_media_vars))

    temp = [var in dt_input.columns for var in paid_media_spends]
    if not all(temp): ## Manually corrected
        raise ValueError("Input 'paid_media_spends' not included in data. Check: " + str(paid_media_spends[~temp]))

    ## Missed code part, Manually added
    if len(paid_media_signs) == 0:
        paid_media_signs = ["positive"] * media_var_count

    # Check if paid_media_signs are in OPTS_PDN
    ## if not all(paid_media_signs in OPTS_PDN):
    ## Manually added below.
    if not all(x in OPTS_PDN for x in paid_media_signs):
        raise ValueError("Allowed values for 'paid_media_signs' are: " + str(OPTS_PDN))

    # Check if paid_media_signs is a vector of the same length as paid_media_vars
    if len(paid_media_signs) == 1: ## Manually added
        paid_media_signs = paid_media_signs[0] * media_var_count ## Manually added
        ## raise ValueError("Input 'paid_media_signs' must have the same length as 'paid_media_vars'"), manually commented out

    if len(paid_media_signs) != media_var_count:
        raise ValueError("Input 'paid_media_signs' must have the same length as 'paid_media_vars'")

    ## Manually added
    if spend_var_count != media_var_count:
        raise ValueError("Input 'paid_media_spends' must have the same length as 'paid_media_vars'")

    # Check if dt_input[paid_media_vars] are numeric
    ## Manually to be corrected: This part should check all columns of dt_input with names given with paid_media_vars to confirm all numeric
    ## is_num = dt_input[paid_media_vars].apply(lambda x: x.isnumeric())
    ## if not all(is_num):
    if not all(dt_input[paid_media_vars].apply(lambda s: pd.to_numeric(s, errors='coerce').notnull().all()) == True):
        raise ValueError("All your 'paid_media_vars' must be numeric. Check: " + str(paid_media_vars))

    # Check if dt_input[paid_media_vars] are non-negative
    # Manually commented out get_cols = dt_input[paid_media_vars].apply(lambda x: any(x < 0)), need to get unique names first
    vars_list = [paid_media_vars, paid_media_spends]
    unique_cols = list(set().union(*vars_list)) ## Added manually
    ## if pd.to_numeric(dt_input[paid_media_vars], errors='coerce').notnull().all():
    if any(dt_input[unique_cols].lt(0).any()):
        ## check_media_names = dt_input[paid_media_vars].columns[get_cols] , no need.
        ## df_check = dt_input[check_media_names], no need
        negative_list = dt_input[unique_cols].lt(0).any(axis=0).index.to_list() ## Added Manually, check false ones only.
        ## check_media_val = df_check.apply(lambda x: any(x < 0))
        raise ValueError("Contains negative values. Media must be >=0: " + str(negative_list))

    ## Manually corrected
    return {
        "paid_media_signs" : paid_media_signs,
        "mediaVarCount" : media_var_count,
        "paid_media_signs" : paid_media_vars
    }


def check_organicvars(dt_input, organic_vars, organic_signs):
    """
    Checks that the input variables are present in the data and that the signs are valid.
    """
    if organic_vars is None:
        return None

    ## Manually added
    if organic_signs is None:
        organic_signs = list()

    ## Manually corrected: uncomment next section and add check_vector
    # Check that organic_vars is a vector
    ## if not isinstance(organic_vars, list) and not isinstance(organic_vars, np.ndarray):
    ##    raise ValueError("organic_vars must be a vector")
    check_vector(organic_vars)

    ## Manually corrected: uncomment next section and add check_vector
    # Check that organic_signs is a vector
    ## if not isinstance(organic_signs, list) and not isinstance(organic_signs, np.ndarray):
    ##    raise ValueError("organic_signs must be a vector")
    check_vector(organic_signs)

    # Check that organic_vars are present in the data
    temp = [var in dt_input.columns for var in organic_vars]
    if not all(temp):
        raise ValueError("Input 'organic_vars' not included in data. Check:")

    # Check that organic_signs are valid
    ## Manually Corrected to because logical var checks are different in R and Python when it is a Null value
    ## if organic_signs is None:
    if len(organic_signs) == 0 and len(organic_vars) > 0:
        organic_signs = ["positive"] * len(organic_vars)

    ## Wrong translation, Manually commented out
    ## elif not all(sign in ["positive", "negative"] for sign in organic_signs):
    ##    raise ValueError("Allowed values for 'organic_signs' are: positive, negative")
    ## Manually corrected to
    if all(var in OPTS_PDN for var in organic_signs):
       ValueError("Allowed values for 'organic_signs' are: ", OPTS_PDN)

    # Check that organic_signs has the same length as organic_vars
    if len(organic_signs) != len(organic_vars):
        raise ValueError("Input 'organic_signs' must have same length as 'organic_vars'")

    ## MAnually corrected to
    ## return [("organic_signs", organic_signs)]
    return {"organic_signs": organic_signs}


def check_factorvars(dt_input, factor_vars=None, context_vars=None, organic_vars=None):
    """
    Checks if the input variables are numeric and sets factor variables accordingly.
    """

    # Check if factor_vars is a vector
    ## Manually added converting factor_vars to list, otherwise null
    if factor_vars is None:
        factor_vars = []

    ## Below is not necessary for Python, because in R sometimes single vars are passed as a string and then converted to list
    ## if not isinstance(factor_vars, list):
    ##    factor_vars = [factor_vars]

    # Check if context_vars and organic_vars are vectors
    ## Manual: this is unnecessary for python
    ## if not isinstance(context_vars, list):
    ##    context_vars = [context_vars]
    ## if not isinstance(organic_vars, list):
    ##    organic_vars = [organic_vars]
    check_vector(factor_vars)
    check_vector(context_vars)
    check_vector(organic_vars)

    # Select columns from dt_input
    ## Manually corrected to
    # temp = dt_input.select(context_vars, organic_vars)
    temp = dt_input[context_vars + organic_vars]

    # Check if columns are numeric
    ## Manually corrected to get non_numeric columns
    ## are_not_numeric = temp.apply(lambda x: not x.is_numeric).any()
    are_not_numeric = temp.apply(lambda s: not pd.to_numeric(s, errors='coerce').notnull().all()) ## pd.series

    # Find columns that are not numeric and are not in factor_vars
    ## Manually corrected to
    ## these = are_not_numeric[not are_not_numeric.index.isin(factor_vars)]
    if any(are_not_numeric):
        not_numeric = list()
        for val in are_not_numeric.index.values:
            if are_not_numeric[val] == True:
                not_numeric.append(val)

        these = list(np.setdiff1d(not_numeric, factor_vars))

        # Convert these to a list
        ## Redundant for Python, commented out these already a list
        ##these = list(these.index[these])

        # Add these variables to factor_vars
        ## Manually corrected if these is empty or not
        if len(these) > 0:
            print(f"Automatically set these variables as 'factor_vars': {these}")
            factor_vars = factor_vars + these

    # Check if factor_vars are in context_vars and organic_vars
    ## Manually corrected to check all vars, not single line, maybe there are methods for that
    ## if not all(factor_vars in context_vars + organic_vars):
    if factor_vars is not None:
        combined_vars = context_vars + organic_vars
        if not all(var in combined_vars for var in factor_vars):
            raise ValueError("Input 'factor_vars' must be any from 'context_vars' or 'organic_vars' inputs")

    return factor_vars


def check_allvars(all_ind_vars):
    if len(all_ind_vars) != len(set(all_ind_vars)):
        raise ValueError("All input variables must have unique names")


def check_datadim(dt_input, all_ind_vars, rel=10):
    num_obs = dt_input.shape[0]
    if num_obs < len(all_ind_vars) * rel:
        warnings.warn(f"There are {len(all_ind_vars)} independent variables and {num_obs} data points. We recommend row:column ratio of {rel} to 1")
    if dt_input.shape[1] <= 2:
        raise ValueError("Provide a valid 'dt_input' input with at least 3 columns or more")


def check_windows(dt_input, date_var, all_media, window_start=None, window_end=None):
    # Convert date variable to datetime object
    ## Manually corrected: dates_vec is a series need to be np.array or list
    ## dates_vec = pd.to_datetime(dt_input[date_var], origin='1970-01-01')
    dates_vec = pd.to_datetime(dt_input[date_var], format='%Y-%m-%d', origin='unix').values

    # Check and set window_start
    if window_start is None:
        window_start = dates_vec.min()
    else:
        ## Manually corrected, removed
        ## window_start = pd.to_datetime(window_start, format='%Y-%m-%d', origin='1970-01-01')
        window_start = np.datetime64(window_start)
        ## Manually corrected is None
        if window_start is None:
            raise ValueError("Input 'window_start' must have date format, i.e. '{}'".format(datetime.today().strftime('%Y-%m-%d')))
        elif window_start < dates_vec.min():
            window_start = dates_vec.min()
            print("Input 'window_start' is smaller than the earliest date in input data. It's automatically set to the earliest date: {}".format(window_start))

    # Find the index of the closest date to window_start
    ## Manually corrected, removed idxmin to np.argmin to get min index
    rollingWindowStartWhich = np.argmin(abs(dates_vec - window_start)) + 1 ##, R shows 7 but Python has 0 based index.

    if window_start not in dates_vec:
        ## Manually corrected, removed [0] from end of the statement
        window_start = dt_input.loc[rollingWindowStartWhich - 1, date_var]
        print("Input 'window_start' is adapted to the closest date contained in input data: {}".format(window_start))

    refreshAddedStart = window_start

    # Check and set window_end
    if window_end is None:
        window_end = dates_vec.max()
    else:
        ## Manually corrected, removed
        ## window_end = pd.to_datetime(window_end, format='%Y-%m-%d', origin='1970-01-01')
        window_end = np.datetime64(window_end)
        ## Manually corrected is None
        if window_end is None:
            raise ValueError("Input 'window_end' must have date format, i.e. '{}'".format(datetime.today().strftime('%Y-%m-%d')))
        elif window_end > dates_vec.max():
            window_end = dates_vec.max()
            print("Input 'window_end' is larger than the latest date in input data. It's automatically set to the latest date: {}".format(window_end))
        elif window_end < window_start:
            window_end = dates_vec.max()
            print("Input 'window_end' must be >= 'window_start'. It's automatically set to the latest date: {}".format(window_end))

    # Find the index of the closest date to window_end
    ## Manually corrected, removed idxmin to np.argmin to get min index
    rollingWindowEndWhich = np.argmin(abs(dates_vec - window_end)) + 1

    if window_end not in dates_vec:
        ## Manually corrected, removed [0] from end of the statement
        window_end = dt_input.loc[rollingWindowEndWhich - 1, date_var]
        print("Input 'window_end' is adapted to the closest date contained in input data: {}".format(window_end))

    rollingWindowLength = rollingWindowEndWhich - rollingWindowStartWhich + 1

    # Select media channels and check for zeros
    dt_init = dt_input.loc[(rollingWindowStartWhich - 1):(rollingWindowEndWhich - 1), all_media]
    init_all0 = dt_init.select_dtypes(include='number').sum(axis=0) == 0

    if any(init_all0):
        raise ValueError("These media channels contain only 0 within training period {} to {}: {}".format(dt_input.loc[rollingWindowStartWhich - 1, date_var][0], dt_input.loc[rollingWindowEndWhich - 1, date_var][0], ', '.join(dt_init[init_all0.index.values].columns.values)))

    output = {
        'dt_input': dt_input,
        'window_start': window_start,
        'rollingWindowStartWhich': rollingWindowStartWhich,
        'refreshAddedStart': refreshAddedStart,
        'window_end': window_end,
        'rollingWindowEndWhich': rollingWindowEndWhich,
        'rollingWindowLength': rollingWindowLength
    }
    return output


def check_adstock(adstock):
    if adstock is None:
        raise ValueError("Input 'adstock' can't be NULL. Set any of: 'geometric', 'weibull_cdf' or 'weibull_pdf'")

    if adstock == "weibull":
        adstock = "weibull_cdf"

    if adstock not in ["geometric", "weibull_cdf", "weibull_pdf"]:
        raise ValueError("Input 'adstock' must be 'geometric', 'weibull_cdf' or 'weibull_pdf'")

    return adstock


def check_hyperparameters(hyperparameters=None, adstock=None, paid_media_spends=None, organic_vars=None, exposure_vars=None):
    """
    Checks the hyperparameters for the model.
    """
    if hyperparameters is None:
        warnings.warn("Input 'hyperparameters' not provided yet. To include them, run robyn_inputs(InputCollect = InputCollect, hyperparameters = ...)")
        return None
    ## Manually corrected, check columns of hyperparameters DF not dict
    if "train_size" not in hyperparameters.columns:
        hyperparameters["train_size"] = [0.5, 0.8]
        warnings.warn("Automatically added missing hyperparameter range: 'train_size' = c(0.5, 0.8)")

    # Non-adstock hyperparameters check
    check_train_size(hyperparameters)

    # Adstock hyperparameters check
    ## hyperparameters_ordered = hyperparameters.copy()
    hyperparameters_ordered = hyperparameters.copy(deep=True)
    hyperparameters_ordered = hyperparameters_ordered.reindex(sorted(hyperparameters_ordered.columns), axis=1)

    ##get_hyp_names = list(hyperparameters_ordered.keys())
    get_hyp_names = hyperparameters_ordered.columns.values
    ## original_order = [get_hyp_names.index(x) for x in get_hyp_names]
    original_order = hyperparameters.columns.values

    ref_hyp_name_spend = hyper_names(adstock, all_media=paid_media_spends)
    ref_hyp_name_expo = hyper_names(adstock, all_media=exposure_vars)
    ref_hyp_name_org = hyper_names(adstock, all_media=organic_vars)
    ## ref_hyp_name_other = get_hyp_names[get_hyp_names not in HYPS_OTHERS]
    ref_hyp_name_other = [var for var in get_hyp_names if var in HYPS_OTHERS]

    ref_all_media = sorted(ref_hyp_name_spend + ref_hyp_name_org + HYPS_OTHERS)
    ## Added missing lists
    all_ref_names = ref_hyp_name_spend + ref_hyp_name_expo + ref_hyp_name_org + HYPS_OTHERS
    ## all_ref_names = all_ref_names[all_ref_names.index(get_hyp_names)]
    all_ref_names.sort()

    ##if not all(get_hyp_names == all_ref_names):
    if not all([var in all_ref_names for var in get_hyp_names]):
        wrong_hyp_names = [x for x in get_hyp_names if x not in all_ref_names]
        raise ValueError(f"Input 'hyperparameters' contains following wrong names: {', '.join(wrong_hyp_names)}")

    total = len(get_hyp_names)
    total_in = len(ref_hyp_name_spend + ref_hyp_name_org + ref_hyp_name_other)
    if total != total_in:
        raise ValueError(f"{total} hyperparameter values are required, and {total_in} were provided.")

    # Old workflow: replace exposure with spend hyperparameters
    ## if any(get_hyp_names == ref_hyp_name_expo):
    if any([var in ref_hyp_name_expo for var in get_hyp_names]):
        get_expo_pos = [i for i, x in enumerate(get_hyp_names) if x in ref_hyp_name_expo]
        get_hyp_names[get_expo_pos] = ref_all_media[get_expo_pos]
        hyperparameters_ordered = {x: y for x, y in zip(get_hyp_names, hyperparameters_ordered)}

    check_hyper_limits(hyperparameters_ordered, "thetas")
    check_hyper_limits(hyperparameters_ordered, "alphas")
    check_hyper_limits(hyperparameters_ordered, "gammas")
    check_hyper_limits(hyperparameters_ordered, "shapes")
    check_hyper_limits(hyperparameters_ordered, "scales")

    return hyperparameters_ordered


def check_train_size(hyps):
    if "train_size" in hyps:
        if not 1 <= len(hyps["train_size"]) <= 2:
            raise ValueError("Hyperparameter 'train_size' must be length 1 (fixed) or 2 (range)")
        if any(hyps["train_size"] <= 0.1) or any(hyps["train_size"] > 1):
            raise ValueError("Hyperparameter 'train_size' values must be defined between 0.1 and 1")


def check_hyper_limits(hyperparameters, hyper):
    #hyper_which = [i for i, v in enumerate(hyperparameters) if v.endswith(hyper)]
    hyper_which = [v for v in hyperparameters if v.endswith(hyper)]
    ## if not hyper_which:
    if len(hyper_which) == 0:
        return
    limits = hyper_limits()[hyper]
    for i in hyper_which:
        values = hyperparameters[i]
        # Lower limit
        ## ineq = f"{values[0]} <= {limits[0]}"
        ineq = f"{values[0]}{limits[0]}"
        ##lower_pass = eval(parse(text=ineq))
        lower_pass = eval(ineq)
        if not lower_pass:
            raise ValueError(f"{hyperparameters.name[i]}'s hyperparameter must have lower bound {limits[0]}")
        # Upper limit
        ## ineq = f"{values[1]} <= {limits[1]}"
        ineq = f"{values[1]}{limits[1]}"
        ## upper_pass = eval(parse(text=ineq)) or len(values) == 1
        upper_pass = eval(ineq) or len(values) == 1
        if not upper_pass:
            raise ValueError(f"{hyperparameters.keys()[i]}'s hyperparameter must have upper bound {limits[1]}")
        # Order of limits
        order_pass = True if values[0] <= values[1] else False
        if not order_pass:
            raise ValueError(f"{hyperparameters.name[i]}'s hyperparameter must have lower bound first and upper bound second")


def check_calibration(dt_input, date_var, calibration_input, dayInterval, dep_var,
                      window_start, window_end, paid_media_spends, organic_vars):
    ## To be debugged when calibration_input provided
    if calibration_input is not None:
        calibration_input = pd.DataFrame(calibration_input)
        these = ["channel", "liftStartDate", "liftEndDate", "liftAbs", "spend", "confidence", "metric", "calibration_scope"]
        if not all(these in calibration_input.columns.values): ## Added values
            raise ValueError("Input 'calibration_input' must contain columns: " + str(these) + ". Check the demo script for instruction.")
        if not calibration_input["liftAbs"].apply(lambda x: isinstance(x, float) and not np.isnan(x)).all():
            raise ValueError("Check 'calibration_input$liftAbs': all lift values must be valid numerical numbers")
        all_media = paid_media_spends + organic_vars
        cal_media = [item.strip() for item in calibration_input["channel"].str.split("+|,|;|\s")]
        if not all([item in all_media for item in cal_media]):
            these = [item for item in cal_media if item not in all_media]
            raise ValueError("All channels from 'calibration_input' must be any of: " + str(all_media) + ". Check: " + str(these))
        for i in range(len(calibration_input)):
            temp = calibration_input.iloc[i]
            if temp["liftStartDate"] < window_start or temp["liftEndDate"] > window_end:
                raise ValueError("Your calibration's date range for " + temp["channel"] + " between " + temp["liftStartDate"] + " and " + temp["liftEndDate"] + " is not within modeling window (" + window_start + " to " + window_end + "). Please, remove this experiment from 'calibration_input'.")
            if temp["liftStartDate"] > temp["liftEndDate"]:
                raise ValueError("Your calibration's date range for " + temp["channel"] + " between " + temp["liftStartDate"] + " and " + temp["liftEndDate"] + " should respect liftStartDate <= liftEndDate. Please, correct this experiment from 'calibration_input'.")
        if "spend" in calibration_input.columns.values:
            for i in range(len(calibration_input["channel"])): ## added channel
                temp = calibration_input.iloc[i]
                temp2 = cal_media[i]
                if all([item in organic_vars for item in temp2]):
                    continue
                dt_input_spend = dt_input.loc[dt_input[date_var] >= temp["liftStartDate"] & dt_input[date_var] <= temp["liftEndDate"], temp2].sum().round(0)
                if dt_input_spend > temp["spend"] * 1.1 or dt_input_spend < temp["spend"] * 0.9:
                    warnings.warn("Your calibration's spend (" + str(temp["spend"]) + ") for " + temp["channel"] + " between " + temp["liftStartDate"] + " and " + temp["liftEndDate"] + " does not match your dt_input spend (~" + str(dt_input_spend) + "). Please, check again your dates or split your media inputs into separate media channels.")
        if "confidence" in calibration_input.columns:
            for i in range(len(calibration_input)):
                temp = calibration_input.iloc[i]
                if temp["confidence"] < 0.8:
                    warnings.warn("Your calibration's confidence for " + temp["channel"] + " between " + temp["liftStartDate"] + " and " + temp["liftEndDate"] + " is lower than 80%%, thus low-confidence. Consider getting rid of this experiment and running it again.")
        if "metric" in calibration_input.columns:
            for i in range(len(calibration_input)):
                temp = calibration_input.iloc[i]
                if temp["metric"] != dep_var:
                    raise ValueError("Your calibration's metric for " + temp["channel"] + " between " + temp["liftStartDate"] + " and " + temp["liftEndDate"] + " is not '" + dep_var + "'. Please, remove this experiment from 'calibration_input'.")
        if "scope" in calibration_input.columns: ## removed calibration_ before scope
            these = ["immediate", "total"]
            if not all([item in these for item in calibration_input["calibration_scope"]]):
                raise ValueError("Inputs in 'calibration_input$calibration_scope' must be any of: " + str(these))
    return calibration_input


def check_obj_weight(calibration_input, objective_weights, refresh):
    obj_len = 2 if isinstance(calibration_input, type(None)) else 3
    if not isinstance(objective_weights, type(None)):
        if len(objective_weights) != obj_len:
            raise ValueError(f"objective_weights must have length of {obj_len}")
        if any([weight < 0 or weight > 10 for weight in objective_weights]):
            raise ValueError("objective_weights must be >= 0 & <= 10")
    if isinstance(objective_weights, type(None)) and refresh:
        if obj_len == 2:
            objective_weights = [1, 10]
        else:
            objective_weights = [1, 10, 10]
    return objective_weights


def check_iteration(calibration_input, iterations, trials, hyps_fixed, refresh):
    if not refresh:
        if not hyps_fixed:
            if calibration_input is None and (iterations < 2000 or trials < 5):
                warnings.warn("We recommend to run at least 2000 iterations per trial and 5 trials to build initial model")
            else:
                if iterations < 2000 or trials < 10:
                    warnings.warn(f"You are calibrating MMM. We recommend to run at least 2000 iterations per trial and {10} trials to build initial model")
    return

## def check_InputCollect(list):
def check_input_collect(input_collect):
    names_list = ["dt_input", "paid_media_vars", "paid_media_spends", "context_vars", "organic_vars", "all_ind_vars", "date_var", "dep_var",
                  "rollingWindowStartWhich", "rollingWindowEndWhich", "mediaVarCount", "factor_vars", "prophet_vars", "prophet_signs", "prophet_country",
                  "intervalType", "dt_holidays"]
    if not all([var in input_collect.keys() for var in names_list]):
        not_present = [name for name in names_list if name not in input_collect.keys()]
        raise ValueError(f"Some elements where not provided in your inputs list: {', '.join(not_present)}")

    if len(input_collect['dt_input']) <= 1:
        raise ValueError('Check your \'dt_input\' object')

    return


def check_robyn_name(robyn_object, quiet=False):
    if not isinstance(robyn_object, type(None)):
        if not os.path.exists(robyn_object):
            file_end = os.path.basename(robyn_object)[-4:]
            if file_end != '.RDS':
                raise ValueError("Input 'robyn_object' must has format .RDS")
        else:
            if not quiet:
                print(f"Skipping export into RDS file")
    return


def check_dir(plot_folder):
    file_end = os.path.basename(plot_folder)[-3:]
    if file_end == '.RDS':
        plot_folder = os.path.dirname(plot_folder)
        print(f"Using robyn object location: {plot_folder}")
    else:
        plot_folder = os.path.join(os.path.dirname(plot_folder), os.path.basename(plot_folder))
    if not os.path.exists(plot_folder):
        plot_folder = os.getcwd()
        print(f"WARNING: Provided 'plot_folder' doesn't exist. Using current working directory: {plot_folder}")
    return plot_folder


def check_calibconstr(calibration_constraint, iterations, trials, calibration_input, refresh):
    if not calibration_input and not refresh:
        total_iters = iterations * trials
        if calibration_constraint < 0.01 or calibration_constraint > 0.1:
            warnings.warn(f"Input 'calibration_constraint' must be >= 0.01 and <= 0.1. Changed to default: 0.1")
            calibration_constraint = 0.1
        models_lower = 500
        if total_iters * calibration_constraint < models_lower:
            warnings.warn(f"Input 'calibration_constraint' set for top {calibration_constraint * 100}% calibrated models. {round(total_iters * calibration_constraint, 0)} models left for pareto-optimal selection. Minimum suggested: {models_lower}")
    return calibration_constraint


def check_hyper_fixed(input_collect, dt_hyper_fixed, add_penalty_factor):
    hyper_fixed = False if dt_hyper_fixed is None else True ## manually fixed
    hyp_param_sam_name = hyper_names(adstock=input_collect.adstock, all_media=input_collect.all_media)
    hyp_param_sam_name = np.concatenate((hyp_param_sam_name, HYPS_OTHERS))
    if add_penalty_factor:
        for_penalty = np.array(input_collect.dt_mod.columns)[np.logical_not(np.isin(input_collect.dt_mod.columns, ['ds', 'dep_var']))]
        hyp_param_sam_name = np.concatenate((hyp_param_sam_name, [f'{p}_penalty' for p in for_penalty]))
    if hyper_fixed:
        dt_hyper_fixed = pd.DataFrame(dt_hyper_fixed)
        if len(dt_hyper_fixed) != 1:
            raise ValueError("Provide only 1 model / 1 row from OutputCollect$resultHypParam or pareto_hyperparameters.csv from previous runs")
        if not all(hyp_param_sam_name in dt_hyper_fixed.columns):
            raise ValueError("Input 'dt_hyper_fixed' is invalid. Please provide 'OutputCollect$resultHypParam' result from previous runs or 'pareto_hyperparameters.csv' data with desired model ID. Missing values for:", hyp_param_sam_name)
    return hyper_fixed


def check_parallel():
    return 'unix' in platform().OS.type


def check_parallel_plot():
    return 'Darwin' not in Sys.info()['sysname']


def check_init_msg(input_collect, cores):
    opt = sum(lapply(input_collect.hyper_updated, len) == 2)
    fix = sum(lapply(input_collect.hyper_updated, len) == 1)
    det = f"({opt} to iterate + {fix} fixed)"
    base = f"Using {input_collect.adstock} adstocking with {len(input_collect.hyper_updated)} hyperparameters {det}"
    if cores == 1:
        print(base + "with no parallel computation")
    else:
        if check_parallel():
            print(base + "on " + str(cores) + " cores")
        else:
            print(base + "on 1 core (Windows fallback)")


def check_class(x: list, object):
    for c in x: ## Manually fixed
        if not isinstance(c, object):
            raise ValueError(f"Input object must be class {x}")
    ## if not x in class(object):


def check_allocator_constrains(low, upr):
    max_length = max(len(low), len(upr))
    if any(low < 0):
        raise ValueError("Inputs 'channel_constr_low' must be >= 0")
    if len(upr) != len(low):
        raise ValueError("Inputs 'channel_constr_up' and 'channel_constr_low' must have the same length or length 1")
    if any(upr < low):
        raise ValueError("Inputs 'channel_constr_up' must be >= 'channel_constr_low'")


def check_allocator(OutputCollect, select_model, paid_media_spends, scenario, channel_constr_low, channel_constr_up, constr_mode):
    check_allocator_constrains(channel_constr_low, channel_constr_up)
    if select_model not in OutputCollect.allSolutions:
        raise ValueError(f"Provided 'select_model' is not within the best results. Try any of: {', '.join(OutputCollect.allSolutions)}")
    if scenario not in ("max_response", "target_efficiency"):
        raise ValueError(f"Input 'scenario' must be one of: {', '.join(('max_response', 'target_efficiency'))}")
    if scenario == "target_efficiency" and not (channel_constr_low is None or channel_constr_up is None):
        raise ValueError("Input 'channel_constr_low' and 'channel_constr_up' must be None for scenario 'target_efficiency'")
    if len(channel_constr_low) != 1 and len(channel_constr_low) != len(paid_media_spends):
        raise ValueError(f"Input 'channel_constr_low' have to contain either only 1 value or have same length as 'paid_media_spends': {len(paid_media_spends)}")
    if len(channel_constr_up) != 1 and len(channel_constr_up) != len(paid_media_spends):
        raise ValueError(f"Input 'channel_constr_up' have to contain either only 1 value or have same length as 'paid_media_spends': {len(paid_media_spends)}")
    if constr_mode not in ("eq", "ineq"):
        raise ValueError(f"Input 'constr_mode' must be one of: {', '.join(('eq', 'ineq'))}")
    return scenario


def check_metric_type(metric_name, paid_media_spends, paid_media_vars, exposure_vars, organic_vars):
    if metric_name in paid_media_spends and len(metric_name) == 1:
        metric_type = "spend"
    elif metric_name in exposure_vars and len(metric_name) == 1:
        metric_type = "exposure"
    elif metric_name in organic_vars and len(metric_name) == 1:
        metric_type = "organic"
    else:
        raise ValueError(f"Invalid 'metric_name' input: {metric_name}")
    return metric_type


def check_metric_dates(all_dates, date_range=None, day_interval=None, quiet=False, is_allocator=False): ## Manually fixed, moved all_dates to first argument.
    """
    Checks the date range and returns the updated date range and location.
    """
    if date_range is None:
        if day_interval is None:
            date_range = "last_30"
        else:
            date_range = f"last_{day_interval}"

    if is_allocator:
        date_range = date_range.replace("last", "").strip()
        if day_interval == 1:
            date_range = f"last_{30}"
        elif day_interval == 7:
            date_range = f"last_{4}"
        else:
            date_range = f"last_{day_interval}"

    if not quiet:
        print(f"Automatically picked date_range = '{date_range}'")

    if "last" in date_range:
        # Using last_n as date_range range
        n = int(date_range.replace("last_", ""))
        date_range_updated = all_dates[n-1:]
        date_range_loc = np.where(all_dates == date_range_updated)[0]
        rg = np.array(date_range_updated).astype(str)
    else:
        # Using dates as date_range range
        date_range_updated = np.array(date_range)
        date_range_loc = np.where(all_dates == date_range_updated)[0]
        rg = np.array(date_range_updated).astype(str)

    return [date_range_updated, date_range_loc]


def check_metric_value(metric_value, metric_name, all_values, metric_loc):
    """
    Checks the metric value and returns the updated metric value and location.
    """
    if np.any(np.isnan(metric_value)):
        metric_value = None

    if not metric_value is None:
        if not np.isnumeric(metric_value):
            raise ValueError(f"Input 'metric_value' for {metric_name} must be a numerical value")

        if np.any(metric_value < 0):
            raise ValueError(f"Input 'metric_value' for {metric_name} must be positive")

        if len(metric_loc) > 1 and len(metric_value) == 1:
            metric_value_updated = np.array(metric_value / len(metric_loc))
            # print(f"'metric_value' {metric_value} splitting into {len(metric_loc)} periods evenly")
        else:
            if len(metric_value) != len(metric_loc):
                raise ValueError("robyn_response metric_value & date_range must have same length")
            metric_value_updated = metric_value

    else:
        metric_value_updated = all_values[metric_loc]

    all_values_updated = all_values.copy()
    all_values_updated[metric_loc] = metric_value_updated

    return [metric_value_updated, all_values_updated]


def check_legacy_input(InputCollect, cores=None, iterations=None, trials=None, intercept_sign=None, nevergrad_algo=None):
    """
    Checks for legacy input parameters and warns the user if they are used.
    """
    if not any([var in InputCollect.keys() for var in LEGACY_PARAMS]):
        return InputCollect

    # Warn the user these InputCollect params will be (are) deprecated
    legacy_values = InputCollect[LEGACY_PARAMS]
    legacy_values = [x for x in legacy_values if x is not None] ## Manually fixed
    if len(legacy_values) > 0:
        warnings.warn(f"Using legacy InputCollect values. Please set {', '.join(LEGACY_PARAMS)} within robyn_run() instead")

    # Overwrite InputCollect with robyn_run() inputs
    if cores is not None:
        InputCollect['cores'] = cores
    if iterations is not None:
        InputCollect['iterations'] = iterations
    if trials is not None:
        InputCollect['trials'] = trials
    if intercept_sign is not None:
        InputCollect['intercept_sign'] = intercept_sign
    if nevergrad_algo is not None:
        InputCollect['nevergrad_algo'] = nevergrad_algo

    InputCollect['deprecated_params'] = True
    return InputCollect


def check_run_inputs(cores, iterations, trials, intercept_sign, nevergrad_algo):
    """
    Checks that the inputs for robyn_run() are valid.
    """
    if iterations is None:
        raise ValueError("Must provide 'iterations' in robyn_run()")
    if trials is None:
        raise ValueError("Must provide 'trials' in robyn_run()")
    if nevergrad_algo is None:
        raise ValueError("Must provide 'nevergrad_algo' in robyn_run()")
    opts = ['non_negative', 'unconstrained']
    if intercept_sign not in opts:
        raise ValueError(f"Input 'intercept_sign' must be any of: {', '.join(opts)}")


def check_daterange(date_min, date_max, dates):
    """
    Checks that the date range for the data is valid.
    """
    if date_min is not None:
        if len(date_min) > 1:
            raise ValueError("Set a single date for 'date_min' parameter")
        if date_min < min(dates):
            warnings.warn(f"Parameter 'date_min' not in your data's date range. Changed to '{min(dates)}'")

    if date_max is not None:
        if len(date_max) > 1:
            raise ValueError("Set a single date for 'date_max' parameter")
        if date_max > max(dates):
            warnings.warn(f"Parameter 'date_max' not in your data's date range. Changed to '{max(dates)}'")


def check_refresh_data(Robyn, dt_input):
    """
    Checks that the refresh data is valid.
    """
    original_periods = len(Robyn['listInit']['InputCollect']['dt_modRollWind'])
    new_periods = len(filter(dt_input, get(Robyn['listInit']['InputCollect']['date_var']) > Robyn['listInit']['InputCollect']['window_end']))
    it = Robyn['listInit']['InputCollect']['intervalType']
    if new_periods > 0.5 * (original_periods + new_periods):
        warnings.warn(f"We recommend re-building a model rather than refreshing this one. More than 50%% of your refresh data ({original_periods + new_periods} {it}) is new data ({new_periods} {it})")


def expand_grid_helper(grep_list, names_list, expand_list):
    """
     Following R method is not available in python.
     local_name <- sort(apply(expand.grid(all_media, HYPS_NAMES[
        grepl("thetas|alphas|gammas", HYPS_NAMES)
        ]), 1, paste, collapse = "_"))
     Therefore, created this helper method
    """
    expanded_list = list()
    if expand_list is None:
        expand_list = list()

    for i in range(len(expand_list)):
        for j in range(len(names_list)):
            if names_list[j] in grep_list:
                new_elem = expand_list[i] + "_" + names_list[j]
                expanded_list.append(new_elem)

    return expanded_list

## Manually added, in R it is in inputs but not possible in Python since it creates transitive dependency
def hyper_names(adstock, all_media):
    adstock = check_adstock(adstock)
    if adstock == "geometric":
        local_name = sorted(expand_grid_helper(["thetas", "alphas", "gammas"], HYPS_NAMES, all_media))
    elif adstock in ["weibull_cdf", "weibull_pdf"]:
        local_name = sorted(expand_grid_helper(["shapes", "scales", "alphas", "gammas"], HYPS_NAMES, all_media))
    return local_name


## Manually added, in R it is in inputs but not possible in Python since it creates transitive dependency
def hyper_limits():
    return pd.DataFrame(
        {
            "thetas": [">=0", "<1"],
            "alphas": [">0", "<10"],
            "gammas": [">0", "<=1"],
            "shapes": [">=0", "<20"],
            "scales": [">=0", "<=1"],
        }
    )