function [W,L] = eigenJacobi(A,B)
% Function computing the weights and nodes of a Gauss-quadrature rule
% from the reccurence coefficients of the three terms relation between
% orthogonal polynomials.
% This function uses the Jacobi iterations method to compute the eigenvalues
% and eigenvectors of the associated jacobi matrix.
%
% >> [W,L] = eigenJacobi(A,B,fc)
%   *Inputs :
%      + A     : Components of main diagonal              (N*1)[double]
%      + B     : Squared components of sub diagonals      (N-1*1)[double]
%      + fc    : Instance of the flopCount class
%   *Outputs :
%      + W     : Row vector of weights                    (1*N)[double]
%      + L     : Column vector of locations               (N*1)[double]
%
% This code is based on the work of John Burkardt who made available a
% similar function written in matlab on his personnal academic web page:
% https://people.sc.fsu.edu/~jburkardt/
% His code is distributed under the GNU LGPL license, a copy of which may
% be found at <https://www.gnu.org/licenses/lgpl-3.0.txt>.

% == RUNNING OPTIONS ==
ITMAX = 100; %Maximum number of iterations to perform

% == FETCHING INFORMATION ==
O = size(A,1);

% == CONSTRUCTING JACOBI MATRIX ==
J = zeros(O,O);
J(1,1) = A(1);
for i=2:O
  J(i,i)=A(i);
  J(i-1,i)=sqrt(B(i-1)); 
  J(i,i-1)=J(i-1,i);
end

% == VARIABLE INITIALISATION ==
V = eye ( O, O );
L = A;
bw = A;
zw = zeros(O,1);
it_num = 0;

% == ITERATIVE RESOLUTION ==
while ( it_num < ITMAX )
  it_num = it_num + 1; 

  % -- Checking convergence -
  thresh = 0;
  for i=1:(O-1)
    for j=i+1:O
      thresh = thresh + abs(J(i,j)); 
    end
  end
  thresh = thresh/(4*O); 
  if ( thresh == 0.0 )
    break;
  end
  
  for p = 1 : O
    for q = p + 1 : O
      gapq = 10 * abs ( J(p,q) ); 
      
      if ( 4 < it_num && gapq < eps(min(abs(L(p)),abs(L(q)))))
        % -- Removing non significant offdiagonal elements --
        J(p,q) = 0;
      elseif ( thresh <= abs ( J(p,q) ) )
        % -- Applying a rotation --
        h = L(q) - L(p); 
        
        if ( gapq < eps(h) )
          t = J(p,q) / h; 
        else
          theta = .5 * h / J(p,q); 
          t = 1 / ( abs ( theta ) + hypot(1,theta) );
          
          if ( theta < 0 )
            t = - t; 
          end
        end
        
        c = 1 / hypot(1,t);
        s = t * c;
        tau = s / ( 1 + c );
        h = t * J(p,q);
       
        
        % -- Accumulate corrections to diagonal elements --
        zw(p) = zw(p) - h;
        zw(q) = zw(q) + h;
        L(p) = L(p) - h;
        L(q) = L(q) + h;
       
        
        J(p,q) = 0;

        % -- Rotate elements --
        for j = 1:p-1
          g = J(j,p);
          h = J(j,q);
          J(j,p) = g - s * ( h + g * tau );
          J(j,q) = h + s * ( g - h * tau );
          
        end
        for j = p+1:q-1
          g = J(p,j);
          h = J(j,q);
          J(p,j) = g - s * ( h + g * tau );
          J(j,q) = h + s * ( g - h * tau );
          
        end
        for j = q+1:O
          g = J(p,j);
          h = J(q,j);
          J(p,j) = g - s * ( h + g * tau );
          J(q,j) = h + s * ( g - h * tau );
         
        end
        % -- Update the eigenvector matrix --
        for j = 1:O
          g = V(j,p);
          h = V(j,q);
          V(j,p) = g - s * ( h + g * tau );
          V(j,q) = h + s * ( g - h * tau );
        
        end
      end
    end
  end
  
  bw = bw + zw; 
  L = bw;
  zw = zw*0; 
end

% == SORTING EIGENVALUES ==
for k = 1 : O - 1
  m = k;
  for l = k + 1 : O
    if ( L(l) < L(m) )
      m = l;
    end
  end
  if ( m ~= k )
    t    = L(m);
    L(m) = L(k);
    L(k) = t;
    w      = V(:,m);
    V(:,m) = V(:,k);
    V(:,k) = w;
  end
end

% == COMPUTING WEIGHTS ==
W = V(1,:).^2; 
end
