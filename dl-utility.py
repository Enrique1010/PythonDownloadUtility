import requests
import os
import re
import six
import sys
import tqdm
import tempfile
import shutil
import bs4


SUPPORTED_SITES = ['mediafire', 'qiwi']

def get_download_link(links, site):
    """
    Function to generate folder names based on the file
    """
    for link in links.splitlines():
        # search for the url that match the actual download link
        if site == 'mediafire':
            download_link = re.search(r'href="((http|https)://download[^"]+)', link)
            if download_link:
                return download_link.groups()[0]
        elif site == 'qiwi':
            soup = bs4.BeautifulSoup(link, 'html.parser')
            ext = soup.find('h1').text.split('.')[-1]  # Get the file extension
            domain = 'https://spyderrock.com/'  # This will probably need to be updated frequently
            download_link = domain + link.split('/file/')[1] + '.' + ext
            print(download_link)
        # other sites downloads (TBD)
        else:
            download_link = None


def generate_folder_name(file_name):
    # Remove the file extension (if any)
    file_name_no_ext = re.sub(r'\..+$', '', file_name)

    # Remove "partX" or "part X" from the filename
    folder_name = re.sub(r'\s*part\s*\d+', '', file_name_no_ext)

    # Strip leading/trailing whitespaces (if any)
    folder_name = folder_name.strip()

    return folder_name


def download_files(download_link, site, chunk_base_size=512):
    original_dl = download_link
    session = requests.session()
    # pretending to be a browser to avoid block errors and so on.
    session.headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # Loop through each link and download the corresponding file
    while True:
        response = session.get(download_link, stream=True)
        if 'Content-Disposition' in response.headers:
            # This is the file
            break

        download_link = get_download_link(response.text, site)

        if download_link is None:
            print("Something went wrong!! try to check the access or permissions or check links.txt urls.")
            return

    file_output = re.search('filename="(.*)"', response.headers['Content-Disposition'])
    output = file_output.groups()[0]
    output = output.encode('iso8859').decode('utf-8')

    output_is_path = isinstance(output, six.string_types)

    print('Downloading...', file=sys.stderr)
    print('From:', original_dl, file=sys.stderr)

    # adding a temp_file
    if output_is_path:
        # Ensure the "downloads" folder exists
        output_folder = f"downloads/{generate_folder_name(output)}"  # Creating a generic folder to save downloads there
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)  # Create the folder if it doesn't exist

        # Creating the temp file
        temp_file = tempfile.mktemp(
            suffix=tempfile.template,
            prefix=os.path.basename(output),
            dir=os.path.dirname(output)
        )

        # Now you can safely open the temp file inside the "downloads" folder
        temp_file_path = os.path.join(output_folder, temp_file)
        file = open(temp_file_path, 'wb')
    else:
        temp_file = None
        file = output

    try:
        # getting the total file size to calculate the progress
        total = response.headers.get('Content-Length')
        if total is not None:
            total = int(total)

        # creating download progress bar for better info
        bar = tqdm.tqdm(total=total, unit='B', unit_scale=True)

        # showing the bar during the file creation process
        # Retrieving the response content in chunks. To process it in smaller parts (or chunks).
        # Base size 512 * 1024 = 524,288 bytes (or 512 KB). This means the content will be downloaded in 512 KB chunks.
        for chunk in response.iter_content(chunk_size=chunk_base_size * 1024):
            # Save the content of the file
            file.write(chunk)
            bar.update(len(chunk))

        # closing bar after download finish
        bar.close()

        # moving download file after download is finished
        if temp_file:
            file.close()
            shutil.move(temp_file, output)

    except IOError as e:
        print(e, file=sys.stderr)
        return
    finally:
        try:
            if temp_file:
                os.remove(temp_file)
        except OSError:
            pass
    return output # just in case


def main():
    # Open the text file containing the links
    with open("links.txt", 'r') as file:
        links = file.readlines()

    print(f"Download utility to perform automatic downloads from {' '.join(SUPPORTED_SITES)}...\n")
    site = input('Enter the site you want to download from: ') or 'mediafire'

    if site not in SUPPORTED_SITES:
        print(f"Site {site} not supported, please try a valid site. \n")
        return

    try:
        for download_link in links:
            download_link = download_link.strip()  # Properly update download_link
            download_files(download_link=download_link, site=site)

    except KeyboardInterrupt:
        print("\n Downloads cancelled by the user!")


if __name__ == "__main__":
    main()