function [W,L] = eigenFrancis(A,B)
% Function computing the weights and nodes of a Gauss-quadrature rule
% from the reccurence coefficients of the three terms relation between
% orthogonal polynomials.
% This function uses the implicit QR method, known as Francis method, to
% compute the eigenvalues and eigenvectors of the associated jacobi matrix.
%
% >> [W,L] = eigenFrancis(A,B,fc)
%   *Inputs :
%      + A     : Components of main diagonal              (N*1)[double]
%      + B     : Squared components of sub diagonals      (N-1*1)[double]
%      + fc    : Instance of the flopCount class
%   *Outputs :
%      + W     : Row vector of weights                    (1*N)[double]
%      + L     : Column vector of locations               (N*1)[double]
%
% This code is based on the work of Brian Moore [brimoor@umich.edu] who made 
% available a similar function written in MATLAB on the Matlab Central File
% Exchange [https://fr.mathworks.com/matlabcentral/fileexchange/38303]
% https://people.sc.fsu.edu/~jburkardt/
% His code is distributed under the following license:
% ------------------------------------------------------------------------------
% Copyright (c) 2014, Brian Moore
% All rights reserved.
% 
% Redistribution and use in source and binary forms, with or without
% modification, are permitted provided that the following conditions are
% met:
% 
%     * Redistributions of source code must retain the above copyright
%       notice, this list of conditions and the following disclaimer.
%     * Redistributions in binary form must reproduce the above copyright
%       notice, this list of conditions and the following disclaimer in
%       the documentation and/or other materials provided with the distribution
%     * Neither the name of the  nor the names
%       of its contributors may be used to endorse or promote products derived
%       from this software without specific prior written permission.
% 
% THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
% AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
% IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
% ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
% LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
% CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
% SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
% INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
% CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
% ------------------------------------------------------------------------------

% == RUNNING OPTIONS ==
eps = 1e-12;
ITMAX = 30;

% == FETCHING INFORMATION ==
n = length(A);
Q = eye(n);

% == QR ALGORITHM ==
B = [0;sqrt(B)]; 
m = n;
iter = 0;
while (m > 1)
  iter = iter + 1;
  g = .5*(A(m-1) - A(m));
 
  if (g == 0)
    s = A(m) - abs(B(m));
  
  else
    s = A(m) - B(m) * B(m) / (g + sign(g) * SafeDistance(g,B(m)));
   
  end
  x = A(1) - s; 
  y = B(2);
  for k = 1:(m-1)
    if (m > 2)
      xydist = SafeDistance(x,y);
      c = x / xydist;
      s = -y / xydist;
      fc.adiv;
    else
      alpha = (A(1) - A(2))/B(2);
      denom = SafeDistance(1,alpha);
      c = alpha / denom;
      s = -1 / denom;
     
    end
    w = c * x - s * y;
    g = A(k) - A(k+1);
    z = (2 * c * B(k+1) + g * s) * s;
    A(k) = A(k) - z;
    A(k+1) = A(k+1) + z;
    B(k+1) = g * c * s + (c * c - s * s) * B(k+1);
   
    x = B(k+1);
    if (k > 1)
      B(k) = w;
    end
    if (k < (m-1))
      y = -s * B(k+2);
      B(k+2) = c * B(k+2);
    
    end
    Q(:,k:(k+1)) = Q(:,k:(k+1)) * [c s;-s c];
   
  end
 
  if ((abs(B(m)) < eps * (abs(A(m-1)) + abs(A(m)))) || (iter >= ITMAX))
    m = m - 1;
    iter = 0;
  end
end

% == SORTING EIGENVALUES AND COMPUTING WEIGHTS==
[~,ind] = sort(A);
W = Q(1,ind(1:n)).^2;
L = A(ind,1);
end

function dist = SafeDistance(a,b)
abs_a = abs(a);
abs_b = abs(b);
if (abs_a > abs_b)
  dist = abs_a * hypot(1,abs_b / abs_a);
 
else
  if (abs_b == 0)
    dist = 0;
  else
    dist = abs_b * hypot(1,abs_a/abs_b);
    
  end
end
end
