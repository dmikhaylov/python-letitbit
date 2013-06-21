Python Letitbit
====================================================
Description
----------------------------------------------------
Simple module for operations with Letitbit filesharing services like uploading files to FTP, checking links and others.
Unfortunately, due to not so good API documentation this module currently doesn't support some features like uploading files to HTTP servers and converting videos to FLV.
Usage
----------------------------------------------------
Just import module in your code and create Letitbit class instance:

    import letitbit
    l = letitbit.Letitbit('your API key')
    # uploading file with FTP, returns tuple containing link to file and it's uid
    link, uid = l.upload_file('/path/to/your/file.txt')
    # returns flv image with screenshots for your converted video
    flv_screens_link = l.get_flv_image('your flv uid')

