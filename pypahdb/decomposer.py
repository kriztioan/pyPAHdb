#!/usr/bin/env python3
"""decomposer.py

Subclassing DecomposerBase to add support for writting results to
disk.

This file is part of pypahdb - see the module docs for more
information.

"""

import copy
import decimal
import time

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np

from astropy.io import fits
from astropy.wcs import WCS
from matplotlib.backends.backend_pdf import PdfPages

from pypahdb.decomposer_base import DecomposerBase


class Decomposer(DecomposerBase):
    """Extends the DecomposerBase class to write to disk (PDF, FITS)."""

    def __init__(self, spectrum):
        """Initialize a Decomposer object.

        Inherits from the DecomposerBase class of decomposer_base.py.

        Args:
            spectrum (pypahdb.spectrum.Spectrum): The data to fit/decompose.
        """
        DecomposerBase.__init__(self, spectrum)

    def save_pdf(self, filename, header="", domaps=True, doplots=True):
        """Saves a PDF summary of the fit results."""

        def smart_round(value, style="0.1"):
            """Rounds a float nicely, returning a string."""
            tmp = decimal.Decimal(value).quantize(decimal.Decimal(style))
            return str(tmp)

        def _plot_map(im, title, wcs=None):
            """Plots a pyPAHdb map and save to a PDF.

            Notes:
                None.

            Args:
                im (numpy): The map to plot
                title (string): The title

            Keywords:
                wcs (wcs.wcs): wcs (defaults to None).

            Returns:
                fig (matplotlib.figure.Figure): object containing the plot.

            """
            fig = plt.figure(figsize=(8, 11))
            if isinstance(wcs, WCS):
                ax = fig.add_subplot(111, projection=wcs)
            else:
                ax = fig.add_subplot(111)
            ax.grid('on', color='black')
            ax.minorticks_on()
            ax.xaxis.set_tick_params(direction='in',
                                     which='both',
                                     bottom=True,
                                     top=True,
                                     left=True,
                                     right=True)
            ax.yaxis.set_tick_params(direction='in',
                                     which='both',
                                     bottom=True,
                                     top=True,
                                     left=True,
                                     right=True)
            fig.subplots_adjust(left=0.2)
            plt.imshow(im, origin='lower', cmap='viridis',
                       interpolation='nearest')
            ax.set_xlabel(r"Ra [$^{\circ}$ ' '']")
            ax.set_ylabel(r"Dec [$^{\circ}$ ' '']")
            cbar = plt.colorbar(shrink=0.4)
            cbar.set_label(title)
            return fig

        def _plot_fit(i, j):
            """Plots a pypahdb fit and save to a PDF.

            Notes:
                None.

            Args:
                i (int): Pixel coordinate (abscissa).
                j (int): Pixel coordinate (ordinate).

            Keywords:
                domaps (bool): Save maps to PDF (defaults to True)
                doplots (bool): Save plots to PDF (defaults to True)

            Returns:
                fig (matplotlib.figure.Figure): object containing the plot.

            """
            # Create figure, shared axes.
            fig = plt.figure(figsize=(8, 11))
            gs = gridspec.GridSpec(4, 1, height_ratios=[2, 1, 2, 2])
            gs.update(wspace=0.025, hspace=0.00)  # spacing between axes.
            ax0 = fig.add_subplot(gs[0])
            ax1 = fig.add_subplot(gs[1], sharex=ax0)
            ax2 = fig.add_subplot(gs[2], sharex=ax0)
            ax3 = fig.add_subplot(gs[3], sharex=ax0)

            # Common quantities for clarity.
            abscissa = self.spectrum.abscissa
            charge = self.charge

            # ax0 -- Best fit.
            data = self.spectrum.ordinate[:, i, j]
            model = self.fit[:, i, j]
            ax0.plot(abscissa, data, 'kx', ms=5, mew=0.5, label='input')
            ax0.plot(abscissa, model, label='fit', color='red')
            norm_val = self.norm[i][j]
            norm_str = smart_round(norm_val, style="0.1")
            norm_str = '$norm$=' + norm_str
            ax0.text(0.025, 0.9, norm_str, ha='left', va='center',
                     transform=ax0.transAxes)

            # ax1 -- Residuals.
            ax1.plot(abscissa, data - model, lw=1,
                     label='residual', color='black')
            ax1.axhline(y=0, color='0.5', ls='--', dashes=(12, 16),
                        zorder=-10, lw=0.5)

            # ax2 -- Size breakdown.
            ax2.plot(abscissa, model, color='red', lw=1.5)
            ax2.plot(abscissa, self.size['large'][:, i, j],
                     label='large', lw=1, color='purple')
            ax2.plot(abscissa, self.size['small'][:, i, j],
                     label='small', lw=1, color='crimson')
            size_frac = self.large_fraction[i][j]
            size_str = smart_round(size_frac, style="0.01")
            size_str = '$f_{large}$=' + size_str
            ax2.text(0.025, 0.9, size_str, ha='left', va='center',
                     transform=ax2.transAxes)

            # ax3 -- Charge breakdown.
            ax3.plot(abscissa, model, color='red', lw=1.5)
            ax3.plot(abscissa, charge['anion'][:, i, j],
                     label='anion', lw=1, color='orange')
            ax3.plot(abscissa, charge['neutral'][:, i, j],
                     label='neutral', lw=1, color='green')
            ax3.plot(abscissa, charge['cation'][:, i, j],
                     label='cation', lw=1, color='blue')
            ion_frac = self.ionized_fraction[i][j]
            ion_str = smart_round(ion_frac, "0.01")
            ion_str = '$f_{ionized}$=' + ion_str
            ax3.text(0.025, 0.9, ion_str, ha='left', va='center',
                     transform=ax3.transAxes)

            # Plot labels.
            ylabel = self.spectrum.units['ordinate']['str']
            fig.text(0.02, 0.5, ylabel, va='center', rotation='vertical')
            ax3.set_xlabel(self.spectrum.units['abscissa']['str'])

            # Set tick parameters and add legends to all axes.
            for ax in (ax0, ax1, ax2, ax3):
                ax.tick_params(axis='both', which='both', direction='in',
                               top=True, right=True)
                ax.minorticks_on()
                ax.legend(loc=0, frameon=False)

            return fig

        with PdfPages(filename) as pdf:
            d = pdf.infodict()
            d['Title'] = 'pypahdb Result Summary'
            d['Author'] = 'pypahdb'
            d['Subject'] = 'Summary of pypahdb PAH database Decomposition'
            d['Keywords'] = 'pypahdb PAH database'
            if(domaps is True):
                if isinstance(header, fits.header.Header):
                    hdr = copy.deepcopy(header)
                    hdr['NAXIS'] = 2
                    cards = ['NAXIS3', 'PC3_3', 'CRPIX3',
                             'CRVAL3', 'CTYPE3',
                             'CUNIT3', 'PS3_0', 'PS3_1']
                    for c in cards:
                        if c in hdr:
                            del hdr[c]
                    wcs = WCS(hdr)
                else:
                    wcs = None
                fig = _plot_map(self.ionized_fraction,
                                'ionization fraction', wcs=wcs)
                pdf.savefig(fig)
                plt.close(fig)
                plt.gcf().clear()
                fig = _plot_map(self.large_fraction,
                                'large fraction', wcs=wcs)
                pdf.savefig(fig)
                plt.close(fig)
                plt.gcf().clear()
                fig = _plot_map(self.norm, 'norm', wcs=wcs)
                pdf.savefig(fig)
                plt.close(fig)
                plt.gcf().clear()

            if(doplots):
                for i in range(self.spectrum.ordinate.shape[1]):
                    for j in range(self.spectrum.ordinate.shape[2]):
                        fig = _plot_fit(i, j)
                        pdf.savefig(fig)
                        plt.close(fig)
                        plt.gcf().clear()

        return

    def save_fits(self, filename, header=""):
        """Saves a FITS file of the pyPAHdb fit/breakdown."""

        def _fits_to_disk(hdr, filename):
            """Writes the FITS file to disk, with header."""
            hdr['DATE'] = time.strftime("%Y-%m-%dT%H:%m:%S")
            hdr['SOFTWARE'] = "pypahdb"
            hdr['SOFT_VER'] = "0.5.0.a1"
            hdr['COMMENT'] = "This file contains results from a pypahdb fit"
            hdr['COMMENT'] = "Visit https://github.com/pahdb/pypahdb/ " \
                "for more information on pypahdb"
            hdr['COMMENT'] = "The 1st plane contains the ionized fraction"
            hdr['COMMENT'] = "The 2nd plane contains the large fraction"
            hdr['COMMENT'] = "The 3rd plane contains the norm"

            # write results to fits-file
            hdu = fits.PrimaryHDU(np.stack((self.ionized_fraction,
                                            self.large_fraction,
                                            self.norm), axis=0),
                                  header=hdr)
            hdu.writeto(filename, overwrite=True)

            return

        # save results to fits
        if isinstance(header, fits.header.Header):
            # should probably clean up the header
            # i.e., extract certain keywords only
            hdr = copy.deepcopy(header)
        else:
            hdr = fits.Header()

        _fits_to_disk(hdr, filename)

        return
