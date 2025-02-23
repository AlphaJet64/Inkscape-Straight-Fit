import base64
import io
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, Canvas, Tk

import inkex
from inkex import TextElement, Circle, PathElement, Image, Layer
from inkex.elements import Image as InkImage
from inkex.localization import inkex_gettext as _
from inkex.colors import Color
from inkex import units
from PIL import Image as PilImage
import numpy as np

# Retrieve the image folder
# Récupère le dossier image
def get_image_path(filename):
    user_folder = os.path.expanduser('~')
    possible_image_folders = ['Images', 'images', 'Pictures', 'pictures']
    for folder in possible_image_folders:
        image_folder = os.path.join(user_folder, folder)
        if os.path.isdir(image_folder):
            return os.path.join(image_folder, filename)
    return os.path.join(user_folder, 'Images', filename)

# Convert an image to a format that Tkinter can display
# Convertir une image en un format que Tkinter peut afficher
def pil_to_tk(root, image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return tk.PhotoImage(master=root, data=buffer.getvalue())

# Adjust the dimensions of an image to fit the specified dimensions while maintaining the original ratio.
# Ajuste les dimensions d'une image pour s'adapter aux dimensions spécifiées en gardant le ratio d'origine.
def best_fit(oldsize, picsize):
    new_width, new_height = picsize
    old_width, old_height = oldsize
    if new_width * old_height < new_height * old_width:
        new_height = max(1, old_height * new_width // old_width)
    else:
        new_width = max(1, old_width * new_height // old_height)
    return new_width, new_height

# Get all extensions supported by PIL
# Obtenir toutes les extensions supportées par PIL
def get_supported_extensions():
    extensions = PilImage.registered_extensions()
    return [(f"{ext.upper()} files", f"*{ext}") for ext in extensions]

# Sort points starting from the top-left point and moving clockwise
# Trier les points en partant du point en haut à gauche et en tournant en sens trigonométrique
def sort_points(points):
    top = sorted(points, key=lambda p: p[1])[:2]
    bottom = sorted(points, key=lambda p: p[1])[-2:]
    top_sorted = sorted(top, key=lambda p: p[0])
    bottom_sorted = sorted(bottom, key=lambda p: p[0])
    return [top_sorted[0]] + bottom_sorted + [top_sorted[1]]

# Permute a list based on a starting index
# Permuter une liste en fonction d'un index de départ
def permutation(lst, premier):
    n = len(lst)
    index = premier % n
    return lst[index:] + lst[:index]

# Calculate the new cutting coordinates of a path based on the position, dimensions, and DPI of an image.
# Calculer les nouvelles coordonnées de découpe d'un chemin en fonction de la position, des dimensions, et du DPI d'une image.
def coordonnees_decoupe(image_element, image_size, dpi, path_data):
    image_x = float(image_element.get('x', 0))
    image_y = float(image_element.get('y', 0))
    image_width = float(image_element.get('width', 1))
    image_height = float(image_element.get('height', 1))
    real_width, real_height = image_size
    if real_width and real_height:
        scale_x = real_width / image_width
        scale_y = real_height / image_height
        return [((x - image_x) * scale_x, (y - image_y) * scale_y) for x, y in path_data]
    return []

# Parse an SVG transformation string
# Analyser une chaîne de transformation SVG
def parse_transform(transform):
    if not transform:
        return []
    return [(match.group(1), match.group(2).split(',')) for part in transform.split(')') if part.strip() and (match := re.match(r'([a-z]+)\(([^)]+)', part.strip()))]

class Straight_Fit(inkex.EffectExtension):

    # Transform a quadrilateral into a rectangle
    # Transformation d'un quadrilatère en rectangle
    def quadrilatere_to_rectangle(self, image, points, width, height):
        destination_points = [(0, 0), (width, 0), (width, height), (0, height)]
        matrix = np.array(points + destination_points).flatten()
        return image.transform((width, height), PilImage.QUAD, data=matrix, resample=PilImage.BICUBIC)

    # Check that the selection contains exactly one image and one path
    # Vérifier que la sélection contient exactement une image et un chemin
    def get_selection(self):
        if len(self.svg.selection) != 2:
            raise ValueError("Please select exactly two elements.")
            # Veuillez sélectionner exactement deux éléments.
        image_elements = self.svg.selection.get(Image)
        path_elements = self.svg.selection.get(PathElement)
        if len(image_elements) != 1 or len(path_elements) != 1:
            raise ValueError("The selection must contain exactly one image and one path.")
            # La sélection doit contenir exactement une image et un chemin.
        return image_elements[0], path_elements[0]

    # Add the orientation argument
    # Ajouter l'argument d'orientation
    def add_arguments(self, pars):
        pars.add_argument("--orientation", type=int, default=1, help="Choose the top-left point of the page")
        # Choisir le point en haut à gauche de la page

    # Main program
    # Programme principal
    def effect(self):
        try:
            # Get the dimensions of the SVG page
            # Obtenir les dimensions de la page SVG
            unit = self.svg.unit
            page_width = self.svg.viewport_width
            page_height = self.svg.viewport_height
            page_width_px = units.convert_unit(page_width, 'px')
            page_height_px = units.convert_unit(page_height, 'px')
            page_width_unit = units.convert_unit(page_width, unit)
            page_height_unit = units.convert_unit(page_height, unit)

            # Call the get_selection function to check the selection
            # Appeler la fonction get_selection pour vérifier la sélection
            image_element, path_element = self.get_selection()

            # Process the image
            # Traitement de l'image
            image_element_href = image_element.get('xlink:href')
            if not image_element_href:
                raise ValueError("The selected image does not have a valid href attribute.")
                # L'image sélectionnée n'a pas d'attribut href valide.

            if image_element_href.startswith('data:'):
                # Retrieve base64 encoded data
                # Récupérer les données encodées en base64
                header, encoded = image_element_href.split(',', 1)
                image_element_data = base64.b64decode(encoded)
                image_element_file = io.BytesIO(image_element_data)
                transform = image_element.get('transform')
                if transform is not None:
                    raise ValueError(f"The image must not have undergone any transformation here : {transform}")
                    # L'image ne doit avoir subi aucune transformation.
            else:
                image_element_file = self.absolute_href(image_element_href)

            # Process the quadrilateral
            # Traitement du quadrilatère
            end_points_list = list(path_element.path.transform(path_element.composed_transform()).end_points)
            end_points = [(point.x, point.y) for point in end_points_list[:4]]
            sorted_points = sort_points(end_points)
            index_ref = self.options.orientation
            permuted_points = permutation(sorted_points, index_ref - 1)

            with PilImage.open(image_element_file) as image:
                cutting_points = coordonnees_decoupe(image_element, image.size, image.info.get('dpi', (96, 96)), permuted_points)
                transformed_image = self.quadrilatere_to_rectangle(image, cutting_points, int(page_width), int(page_height))

            # Function for buttons to cancel and close the window
            # Fonction des boutons pour annuler et fermer la fenêtre
            def cancel():
                root.destroy()

            # Function to save the image
            # Fonction pour enregistrer l'image
            def save():
                user_images_dir = next((os.path.join(os.path.expanduser('~'), folder) for folder in ['Images', 'images', 'Pictures', 'pictures'] if os.path.isdir(os.path.join(os.path.expanduser('~'), folder))), os.path.expanduser('~'))

                # Create a new layer named "redressement"
                # Créer un nouveau calque nommé "redressement"
                layer = Layer()
                layer.label = "redressement"
                self.svg.add(layer)

                # Convert the transformed image into an in-memory buffer
                # Convertir l'image transformée en un tampon en mémoire
                buffer = io.BytesIO()
                transformed_image.save(buffer, format="PNG")
                buffer.seek(0)

                # Read the image data as binary data from the buffer
                # Lire les données de l'image en tant que données binaires depuis le tampon
                image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

                # Create a new image element with the base64 encoded data
                # Créer un nouvel élément image avec les données encodées en base64
                new_image = InkImage()
                new_image.set('xlink:href', f"data:image/png;base64,{image_data}")
                new_image.set('x', 0)
                new_image.set('y', 0)
                new_image.set('width', page_width_unit)
                new_image.set('height', page_height_unit)

                # Add the image to the layer
                # Ajouter l'image au calque
                layer.add(new_image)

                # Get all extensions supported by PIL
                # Obtenir toutes les extensions supportées par PIL
                supported_extensions = get_supported_extensions()

                file_path = filedialog.asksaveasfilename(
                    initialdir=user_images_dir,
                    initialfile="Fix A4.png",
                    defaultextension=".png",
                    filetypes=supported_extensions)

                if file_path:
                    new_image.save(file_path)

                root.destroy()

            # Dialog box design
            # Design de la boîte de dialogue
            root = Tk()
            root.title("Preview of the transformed image")
            root.attributes("-topmost", True)
            window_width = 350
            window_height = 450
            root.geometry(f"{window_width}x{window_height}")
            root.resizable(False, False)
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            root.geometry(f"+{x}+{y}")
            picsize = (350, 300)
            image_tk = pil_to_tk(root, transformed_image.resize(best_fit(transformed_image.size, picsize), PilImage.LANCZOS))
            canvas = Canvas(root, width=picsize[0], height=picsize[1])
            canvas.grid(row=0, column=0, columnspan=5, pady=20, sticky='ew')
            x = (picsize[0] - image_tk.width()) // 2
            y = (picsize[1] - image_tk.height()) // 2
            canvas.create_image(x, y, anchor='nw', image=image_tk)
            text_label = tk.Label(root, text="The image is added even if you defer saving.\nNo change if canceled and close")
            text_label.grid(row=1, column=0, columnspan=5)
            root.grid_columnconfigure(0, weight=1)
            root.grid_columnconfigure(1, weight=1)
            root.grid_columnconfigure(2, weight=1)
            root.grid_columnconfigure(3, weight=1)
            root.grid_columnconfigure(4, weight=1)
            root.grid_rowconfigure(1, weight=1)
            root.grid_rowconfigure(2, weight=1)
            cancel_button = tk.Button(root, text="Cancel", command=cancel)
            cancel_button = tk.Button(root, text="Annuler", command=cancel)
            cancel_button.grid(row=2, column=1, pady=10)
            save_button = tk.Button(root, text="Save", command=save)
            save_button = tk.Button(root, text="Enregistrer", command=save)
            save_button.grid(row=2, column=3)
            root.mainloop()

        except ValueError as e:
            # Display a custom error message and stop the extension
            # Afficher un message d'erreur personnalisé et arrêter l'extension
            raise inkex.AbortExtension("Error: " + str(e)) from e


if __name__ == "__main__":
    Straight_Fit().run()
