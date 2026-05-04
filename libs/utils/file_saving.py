import datetime
import os
from IPython import get_ipython
import h5py
import json
import numpy as np
import time as timelib
from typing import Callable, Union


def make_path_fn(data_path) -> Callable[[], str]:
    """
    Fonction qui retourne une fonction qui crée un dossier avec la date du jour pour enregistrer des données.
    Le chemin du dossier créé est retourné.
    """
    def path_fn():
        date = datetime.datetime.now().strftime("%Y%m%d")
        path = os.path.join(data_path, date)

        if not os.path.exists(path):
            os.mkdir(path)
        return path + os.path.sep
    
    return path_fn

def expand_filename(filename) -> str:
    """
    Remplace les caractères `%T` du nom d'un fichier par la date du jour à la seconde près.
    """
    filename = filename.replace("%T", datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    return filename

def get_cell_content(cell_number=-1):
    """
    Retourne le contenu d'une cellule préalablement exécutée d'un notebook.
    Par défaut, c'est la dernière cellule utilisée qui est retournée
    """
    return get_ipython().user_ns['In'][cell_number]

def get_file_variables(file, var_to_exclude=list()):
    """
    Retourne l'ensemble des variables d'un fichier importé à l'exception des variables
    commençant par "__" et des variables inclues dans `var_to_exclude`.

    Args:
        file: Fichier importé
        var_to_exclude (list[str]): Liste contenant le nom des variables à ne pas récolter
    
    Returns:
        dict: Dictionnaire contenant les variables du fichier
    """
    variables = dir(file)
    variables = filter(lambda var: not var.startswith("__"), variables)
    variables = filter(lambda var: var not in var_to_exclude, variables)
   
    return {var: file.__dict__[var] for var in variables}

def get_file_code(file):
    """
    Retourne le code d'un fichier importé.
    Args:
        file: Fichier importé
    
    Returns:
        str: Code du fichier
    """
    path = file.__file__
    with open(path, "r", encoding="utf-8") as f:
        txt = "".join(f.readlines())
    return txt


def h5_dump_dict(grp:h5py.File, dict_) -> None:
    """
    Ajoute des dict en tant qu'attributs dans le group "grp" d'un fichier.
    La fonction essaie d'enregistrer les métadonnées directement. Si l'enregistrement
    échoue, les données sont sérialisées.

    Args:
        grp: h5py.File ou h5py.Group
        dict_: dictionnaire
    """
    for key, val in dict_.items():
        try:
            grp.attrs[key] = val
        except TypeError as e:
            grp.attrs[key] = json.dumps(val, indent=2)

    grp.file.flush() # Note: File.file is file so this work even if grp is a File

def _flush_from_res_handles(file, res_handles, print_progress=True) -> bool:
    """
    Flush des données d'un job qua en cours vers le fichier
    Parcours les variables
    - file/data/<out_var>
    Mets à jour ces variables en allant les chercher par le même nom dans res_handles:
    - file/data/<out_var> = res_handles.get(out_var).fetch()

    La modification est faite seulement si de nouvelles données sont présentes.

    Retourne:
        False si les donneés ne sont pas entièrement remplies
        True sinon
    """

    is_complete = not res_handles.is_processing()

    memory_dict = file.memory_dict

    # Extraire et écrire les données
    out_names = file["data"].attrs["result_data_names"]
    for out_name in out_names:
        handle = res_handles.get(out_name)

        last_n = memory_dict.get(out_name, 0)
        n_available = handle.count_so_far()

        if last_n != n_available:
            slc = slice(last_n, n_available)  # Slice pointing to the new data available
            new_data = handle.fetch(slc)["value"]
            memory_dict[out_name] = n_available
            assert file["data"][out_name][slc].shape == new_data.shape, "Problème de tailles. Dans le programme qua, on doit avoir stream.buffer().save_all() pour d=2, stream.save_all() pour d=1"
            file["data"][out_name][slc] = new_data

    file["meta"].attrs["LAST_CALL_TIME"] = current_time = timelib.time()
    creation_time = file["meta"].attrs["CREATION_TIME"]    
    remaining_time_str = ":)"

    if print_progress:     
        name_0, data_0 = out_names[0], file["data"][out_names[0]][:]

        total_points = data_0.shape[0]
        current_point = file.memory_dict.get(name_0, 0)

        if current_point != 0:
            time_per_point = (current_time - creation_time) / current_point
            remaining_time = (total_points - current_point) * time_per_point
            nb_days = int(remaining_time // (3600*24))
            remaining_time_str = timelib.strftime(r"%Hh%Mm%Ss", timelib.gmtime(remaining_time))
            if nb_days != 0:
                remaining_time_str = f"{nb_days}j{remaining_time_str}"

        print(f"Avancement: {current_point}/{total_points}     |    ETA: {remaining_time_str}     ", end="\r")
  
    file.flush()

    return is_complete


def sweep_file(
    filename: str,
    axes_dict: dict[str, Union[int, list]] = {},
    outs_dict: dict[str, tuple[str]] = {},
    print_progress_on_flush: bool = True,
    metadata={},
) -> h5py.File:
    """ 
    Crée et retourne le fichier hdf5.
    Définie une fonction `flush_data(res_handles)` pour ajouter les nouvelles données disponibles.

    Args:
    - axes_dict: dict(ax_name1 = vecteur_de_points, ax_name2 = ...)
        Associe le nom d'un axe a ses valeurs
    - out_dict: dict(stream_name = (axe_name1, axe_name2, axe_name3))
        Associe le nom d'un flux de données au noms de ses dimensions
    
    structure du fichier
    data:
        attrs: 
            "sweeped_ax_names": ["x", "y", ...]
            "result_data_names": ["out1", "out2", ...]«
        x: array
        y: array
        ...
        out1: array  ->  se rempli avec .flush_data(qmjob.res_handles)
        out2: array
        ...
    meta:
        attrs: **metadata


    Clés réservées dans metadata:
    - VERSION
    - CREATION_TIME (0.3+)
    - LAST_CALL_TIME (0.3+)
    """
    # Prepare axes_dict
    for ax, val in axes_dict.items():
        if isinstance(val, int):
            axes_dict[ax] = np.arange(val)
    
    # Make file
    f = h5py.File(filename, "w", libver="latest")
    f.swmr_mode = True
    # meta
    f.create_group("meta")
    ## reserved keys
    metadata["VERSION"] = 0.4
    metadata["CREATION_TIME"] = timelib.time()
    metadata["LAST_CALL_TIME"] = timelib.time()
    h5_dump_dict(f["meta"], metadata)
    ##
    # data
    f.create_group("data")
    data_grp = f["data"]
    data_grp.attrs["sweeped_ax_names"] = list(axes_dict.keys())
    data_grp.attrs["result_data_names"] = list(outs_dict.keys())

    for name, values in axes_dict.items():
        dset = data_grp.create_dataset(name, data=values)
        dset.make_scale(name)
    
    for out_name, axe_names in outs_dict.items():
        dset = data_grp.create_dataset(
            out_name,
            shape=list(map(lambda ax: len(axes_dict[ax]), axe_names)),
            dtype="f",
            fillvalue=np.nan,
        )
        for i, ax_name in enumerate(axe_names):
            dset.dims[i].attach_scale(f["data"][ax_name])
            dset.dims[i].label = ax_name
        dset.attrs["axes"] = axe_names
   
    
    setattr(f, "memory_dict", {})
    setattr(f, "flush_data", lambda res_handles: _flush_from_res_handles(f, res_handles, print_progress=print_progress_on_flush))

    f.flush()

    return f
