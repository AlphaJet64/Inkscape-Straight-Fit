#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" ******    Author: AlphaJet64

Tested with Inkscape version 1.4 windows without select another python environnement 


This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

"""



import inkex
from inkex import Layer
from inkex.elements import Image as InkImage
from PIL import Image as PilImage
import tkinter as tk
from tkinter import filedialog, Canvas, Tk
import os
import base64
import io
import numpy as np


# Save file directory
# Dossier de sauvegarde du fichier
def get_image_path(filename):
    user_folder = os.path.expanduser('~')

    # Possible paths for the Images folder
    # Chemins possibles pour le dossier Images
    possible_image_folders = ['Images', 'images', 'Pictures', 'pictures']

    # Find the existing Images folder
    # Trouver le dossier Images existant
    for folder in possible_image_folders:
        image_folder = os.path.join(user_folder, folder)
        if os.path.isdir(image_folder):
            break
    else:
        # If no Images folder is found, use a default name
        # Si aucun dossier Images n'est trouvé, utiliser un nom par défaut
        image_folder = os.path.join(user_folder, 'Images')

    image_path = os.path.join(image_folder, filename)
    
    return image_path
    
    
    
# Convert an image to a format that Tkinter can display
# Convertir une image en un format que Tkinter peut afficher
def pil_to_tk(root, image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return tk.PhotoImage(master=root, data=buffer.getvalue())
    
# Adjust the dimensions of an image to fit the specified dimensions while maintaining the original ratio
# Ajuste les dimensions d'une image pour s'adapter aux dimensions spécifiées en gardant le ratio d'origine   
def best_fit(oldsize, picsize):
    new_width, new_height = picsize
    old_width, old_height = oldsize
    if new_width * old_height < new_height * old_width:
        new_height = max(1, old_height * new_width // old_width)
    else:
        new_width = max(1, old_width * new_height // old_height)
    return (new_width, new_height)        

# Pillow extensions
# Extensions de Pillow
def get_supported_extensions():
    # Get all extensions supported by PIL
    # Obtenir toutes les extensions supportées par PIL
    extensions = PilImage.registered_extensions()
    supported_extensions = [(f"{ext.upper()} files", f"*{ext}") for ext in extensions]
    return supported_extensions

# Main Class
# Classe Principale
class TransformImageExtension(inkex.EffectExtension):

    def effect(self):

        # Page dimensions
        # Dimensions page
        page_width_mm = self.svg.get('width')
        page_height_mm = self.svg.get('height')
        page_width_value = float(page_width_mm.replace("mm", ""))
        page_height_value = float(page_height_mm.replace("mm", ""))                
        page_width_px = int(self.svg.uutounit(page_width_mm))
        page_height_px = int(self.svg.uutounit(page_height_mm))

        # Check if the quadrilateral and image elements are selected
        # Teste si les élements quadrilatère et image sont bien sélectionnés        
        try:
            message = "Veuillez d'abord sélectionner un quadrilatère fermé ou non ET une image.\n ... Please first select a closed or open quadrilateral AND an image.."
            # Retrieve the points of the selected quadrilateral
            # Récupération des points du quadrilatère sélectionné
            points = self.get_quadrilateral_points()
            if not points:
                raise ValueError(message)

            # Retrieve the selected image
            # Récupération de l'image sélectionnée
            image_elements = self.svg.selection.get(inkex.Image)

            if not image_elements:
                raise ValueError(message)
            image_element = image_elements[0]
            image_href = image_element.get('xlink:href')

            if image_href is None:
                raise ValueError("L'image sélectionnée n'a pas d'attribut href valide.\n The selected image does not have a valid href attribute.")

            if image_href.startswith('data:'):
                # Retrieve the base64 encoded data
                # Récupérer les données encodées en base64
                header, encoded = image_href.split(',', 1)
                image_data = base64.b64decode(encoded)
                image_file = io.BytesIO(image_data)
            else:
                image_file = self.absolute_href(image_href)

            with PilImage.open(image_file) as image:
                image_width, image_height = image.size
                image_dpi = image.info.get('dpi', (96, 96))


                # Image coordinates
                # Coordonnées de l'image
                image_x = float(image_element.get('x', '0'))
                image_y = float(image_element.get('y', '0'))

                # Coordinates of the points relative to the image in general coordinates
                # Coordonnées des points relatives à l'image en coordonnees générales
                points_relative = [(self.svg.uutounit(x - image_x), self.svg.uutounit(y - image_y)) for x, y in points]

                # Sort the relative points to have the first point at the top left and the others counterclockwise
                # Tri des points relatifs pour avoir le premier point le plus en haut à gauche et les autres en sens trigonométrique
                points_relative_sorted = self.sort_points(points_relative)


                # Image rectification, image processing, and retrieving Base64 image
                # Redressement de l'image traitement de l'image et récupération image Base64
                image_transformee = self.quadrilatere_to_rectangle(image, points_relative_sorted, page_width_px, page_height_px)

                
                # ----   Dialog box -------
                # ----   Boite de dialogue -------
                
                # Display the transformed image with tkinter
                # Afficher l'image transformée avec tkinter
                root = Tk()
                root.title("Transformed Image")

                # Load the image as background
                # Charger l'image comme arrière-plan
                picsize = 300, 300
                siz = image_transformee.size

                # Resize the image and convert it for tk
                # Redimensionner l'image et la transformer pour tk
                image_tk = pil_to_tk(root, image_transformee.resize(best_fit(siz, picsize), PilImage.LANCZOS))

                # Create the canvas and display the image
                # Créer le canvas et afficher l'image
                canvas = Canvas(root, width=picsize[0], height=picsize[1])
                canvas.pack()
                
                x = (picsize[0] - image_tk.width()) // 2
                y = (picsize[1] - image_tk.height()) // 2
                canvas.create_image(x, y, anchor='nw', image=image_tk)


                # Function to cancel and close the window
                # Fonction pour annuler et fermer la fenêtre
                def annuler():
                    root.destroy()


                # Function to save the image
                # Fonction pour enregistrer l'image
                def enregistrer():
                    user_images_dir = next((os.path.join(os.path.expanduser('~'), folder) for folder in ['Images', 'images', 'Pictures', 'pictures'] if os.path.isdir(os.path.join(os.path.expanduser('~'), folder))), os.path.expanduser('~'))

                    # Create a new layer named "rectification"
                    # Créer un nouveau calque nommé "redressement"
                    layer = Layer()
                    layer.label = "redressement"
                    self.svg.add(layer)

                    # Convert the transformed image into a memory buffer
                    # Convertir l'image transformée en un tampon en mémoire
                    buffer = io.BytesIO()
                    image_transformee.save(buffer, format="PNG")
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
                    new_image.set('width', page_width_value)
                    new_image.set('height', page_height_value)

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
                        image_transformee.save(file_path)

                    root.destroy()


                # Add the buttons
                # Ajouter les boutons
                bouton_annuler = tk.Button(root, text="Annuler", command=annuler)
                bouton_annuler.pack(side="left", padx=5, pady=5)

                bouton_enregistrer = tk.Button(root, text="Save", command=enregistrer)
                bouton_enregistrer.pack(side="right", padx=5, pady=5)

                root.mainloop()

        except Exception as e:
            inkex.utils.debug(f"Erreur: {e}")


    # Find the coordinates of path points
    # Trouve les coordonnées des points d'un chemin
    def get_quadrilateral_points(self):
        for elem in self.svg.selected.values():
            if isinstance(elem, inkex.PathElement):
                points = []
                for node in elem.path.to_arrays():
                    if node[0] in ['M', 'L']:
                        points.append((node[1][0], node[1][1]))
                if len(points) == 4:
                    return points
        return None

    # Sort the points from the top left in a counterclockwise direction
    # Tri des points depuis le plus en haut à gauche dans le sens trigonométrique
    def sort_points(self, points):
        points_array = np.array(points)
        # Find the point with the smallest x, then the smallest y
        # Trouver le point avec le plus petit x, puis le plus petit y
        start_index = np.lexsort((points_array[:, 1], points_array[:, 0]))[0]
        start_point = points_array[start_index]
        
        # Calculate the angles relative to the start point
        # Calculer les angles par rapport au point de départ
        other_points = np.delete(points_array, start_index, axis=0)
        angles = np.arctan2(other_points[:, 1] - start_point[1], 
                            other_points[:, 0] - start_point[0])
        
        # Sort the other points by angle counterclockwise
        # Trier les autres points par angle dans le sens anti-horaire
        sorted_indices = np.argsort(-angles)  # The negative sign reverses the order for counterclockwise
        sorted_points = np.vstack((start_point, other_points[sorted_indices]))
        return sorted_points.tolist()

    # Main transformation with Pillow of a quadrangular image portion into a rectangle
    # Transformation principale avec Pillow d'une portion d'image quadrangulaire en rectangle
    def quadrilatere_to_rectangle(self, image, points, largeur, hauteur):
        points_destination = [(0, 0), (largeur, 0), (largeur, hauteur), (0, hauteur)]
        matrice = np.array(points + points_destination).flatten()
        image_transformee = image.transform((largeur, hauteur), PilImage.QUAD, data=matrice, resample=PilImage.BICUBIC)
        return image_transformee

if __name__ == '__main__':
    TransformImageExtension().run()

