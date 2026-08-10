function [w,l] = computeGaussWigert(Q,s)
% Method computing the parameters of a Gauss quadrature rules suited to
% approximate integrals weighted by the unshifted LogN distribution 
% over the support (0, +\inf).
%
% int_{0}^{+Inf} f(x) e^(-log(x)^2/(2*s^2))/(x*s*sqrt(2*pi)) dx ~= w * f(l)
%
% >> [w,l] = computeGaussWigert(Q,s)
%   *Inputs :
%      + Q     : Quadrature order                 (1*1)[integer,>1]
%      + s     : shape parameter                  (1*1)[double,>0]
%   *Outputs :
%      + w     : Row vector of weights            (1*Q)[double]
%      + l     : Column vector of nodes           (Q*1)[double]

% == CHECKING INPUTS ==
if numel(Q)~=1 || Q~=uint16(Q) || Q<=1
  error('Wrong order of quadrature.')
end
if numel(s)~=1 || ~isreal(s) || ~isfinite(s) || isnan(s) || s<=0
  error('Invalid shape parameter, s>0 required');
end

% == COMPUTING QUADRATURE ==
z=exp(.5*s*s); z2 = z*z; z3 = z2*z;
C0 = z2; C1 = z; C2 = z;

J = zeros(Q);

J(1,1) = z;
J(2,2) = ((z2+1)*C0-1)*C1;
J(1,2) = sqrt(C0-1)*C2; J(2,1) = J(1,2);
for i=2:Q-1
  C0 = C0*z2; C1 = C1*z2; C2 = C2*z3;
  
  J(i+1,i+1) = ((z2+1)*C0-1)*C1;
  J(i+1,i) = sqrt(C0-1)*C2;
  J(i,i+1) = J(i+1,i);
end

[V,l] = eig(J,'vector');
w = V(1,:).^2;

end