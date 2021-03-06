void ap_ref_gradients(double* restrict x, double* restrict y, LAPACKINDEX num_points,
                      double* restrict ref_dx, double* restrict ref_dy)
{
        double monomials[15*num_points];
        int i;

        /* stuff for dgemm */
        LAPACKINDEX i_twentyone = 21;
        LAPACKINDEX i_fifteen = 15;

#include "coefficients_gradients.h"

        /*
         * Rows in the monomial matrix correspond to monomials (x, y, x^2, etc)
         * while columns correspond to quadrature points. The monomial basis
         * spans quartic polynomials of dimension 2 (hence 15 rows).
         */
        for (i = 0; i < num_points; i++) {
                monomials[ORDER(0,  i, 15, num_points)] = 1.0;
                monomials[ORDER(1,  i, 15, num_points)] = x[i];
                monomials[ORDER(2,  i, 15, num_points)] = y[i];
                monomials[ORDER(3,  i, 15, num_points)] = x[i]*x[i];
                monomials[ORDER(4,  i, 15, num_points)] = x[i]*y[i];
                monomials[ORDER(5,  i, 15, num_points)] = y[i]*y[i];
                monomials[ORDER(6,  i, 15, num_points)] = x[i]*x[i]*x[i];
                monomials[ORDER(7,  i, 15, num_points)] = x[i]*x[i]*y[i];
                monomials[ORDER(8,  i, 15, num_points)] = x[i]*y[i]*y[i];
                monomials[ORDER(9,  i, 15, num_points)] = y[i]*y[i]*y[i];
                monomials[ORDER(10, i, 15, num_points)] = x[i]*x[i]*x[i]*x[i];
                monomials[ORDER(11, i, 15, num_points)] = x[i]*x[i]*x[i]*y[i];
                monomials[ORDER(12, i, 15, num_points)] = x[i]*x[i]*y[i]*y[i];
                monomials[ORDER(13, i, 15, num_points)] = x[i]*y[i]*y[i]*y[i];
                monomials[ORDER(14, i, 15, num_points)] = y[i]*y[i]*y[i]*y[i];
        }

        DGEMM_WRAPPER(i_twentyone, num_points, i_fifteen, coefficients_dx,
                      monomials, ref_dx);
        DGEMM_WRAPPER(i_twentyone, num_points, i_fifteen, coefficients_dy,
                      monomials, ref_dy);
}
